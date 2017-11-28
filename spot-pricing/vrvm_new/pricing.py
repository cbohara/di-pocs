import boto3
import datetime
import pytz
import urllib
import json
import sys
from decimal import Decimal
from awesome_print import ap
from cached_property import cached_property, cached_property_with_ttl

class PricingError(StandardError):
    pass

class Pricing(object):
    pricing_url = 'https://pricing.us-east-1.amazonaws.com'

    def __init__(self, region_name, instance_type):
        self.region_name = region_name
        self.instance_type = instance_type

    def __repr__(self):
        return "Pricing(%s, %s)" % (self.region_name, self.instance_type)

    def instance_price(self, offer_code, offer_code_filter):
        region_index_url = "{0}/offers/v1.0/aws/{1}/current/region_index.json".format(Pricing.pricing_url,offer_code)
        response = urllib.urlopen(region_index_url)
        data = json.loads(response.read())

        if data['regions'].has_key(self.region_name):
            index_url = data['regions'][self.region_name]['currentVersionUrl']
            index_url = Pricing.pricing_url + index_url
        else:
            raise PricingError("Could not find pricing list for region '{}'".format(self.region_name))

        response = urllib.urlopen(index_url)
        data = json.loads(response.read())
        products = data['products'].values()
        products = filter(lambda product: product['attributes'].has_key('instanceType') and product['attributes']['instanceType'] == self.instance_type and offer_code_filter(product), products)

        if products:
            sku = products[0]['sku']
            demand_price = data['terms']['OnDemand'][sku].values()[0]['priceDimensions'].values()[0]['pricePerUnit']['USD']
            return Decimal(demand_price)
        else:
            raise PricingError("Instance type {0} is not available for use in {1}".format(self.instance_type, offer_code))

    def ec2_instant_price(self):
        return self.instance_price('AmazonEC2', lambda product: product['attributes']['operatingSystem'] == 'Linux' and product['attributes']['tenancy'] == 'Shared')

    def emr_instance_price(self):
        return self.instance_price('ElasticMapReduce', lambda product: product['attributes']['softwareType'] == 'EMR')

    @cached_property_with_ttl(ttl=3600)
    def demand_price(self):
        return self.ec2_instant_price()

    @cached_property_with_ttl(ttl=10)
    def lowest_spot_price(self):
        ec2 = boto3.client('ec2', region_name=self.region_name)
        start_time = datetime.datetime.now(pytz.UTC) - datetime.timedelta(minutes=15)

        response = ec2.describe_availability_zones()
        availability_zones = response['AvailabilityZones']
        availability_zones = filter(lambda az: az['State'] == 'available', availability_zones)
        availability_zones = map(lambda az: az['ZoneName'], availability_zones)

        response = ec2.describe_spot_price_history(InstanceTypes=[self.instance_type], ProductDescriptions=['Linux/UNIX','Linux/UNIX (Amazon VPC)'], StartTime=start_time)
        instance_spot_prices = response['SpotPriceHistory']
        latest_spot_prices = []

        for availability_zone in availability_zones:
            #recent_spot_prices = filter(lambda price: price['AvailabilityZone'] == availability_zone and price['Timestamp'] >= start_time, instance_spot_prices)
            availability_zone_spot_prices = filter(lambda price: price['AvailabilityZone'] == availability_zone, instance_spot_prices)
            if availability_zone_spot_prices:
                spot_prices_sorted_by_time = sorted(availability_zone_spot_prices, key=lambda price: price['Timestamp'])
                latest_spot_price = spot_prices_sorted_by_time[-1]
                latest_spot_price['SpotPrice'] = Decimal(latest_spot_price['SpotPrice'])
                latest_spot_prices.append(latest_spot_price)

        if latest_spot_prices:
            lowest_spot_price = min(latest_spot_prices, key=lambda price: price['SpotPrice'])
        else:
            raise PricingError("Could not find any spot price for instance type {0} in region {1}".format(self.instance_type, self.region_name))
        return lowest_spot_price

    @property
    def bid_price(self):
        return "%.3f" % self.demand_price

    @property
    def spot_price(self):
        return self.lowest_spot_price['SpotPrice']

    @property
    def availability_zone(self):
        return self.lowest_spot_price['AvailabilityZone']

    def should_use_spot_price(self):
        return self.spot_price < self.demand_price


def find_reserved_instances(region_name, instance_type):
    ec2 = boto3.client('ec2', region_name=region_name)
    response = ec2.describe_reserved_instances(Filters=[ {'Name':'instance-type','Values':[instance_type]}, {'Name':'state', 'Values':['active']} ])
    return response['ReservedInstances']

def find_available_reserved_instances(region_name, instance_type):
    ec2 = boto3.client('ec2', region_name=region_name)
    response = ec2.describe_reserved_instances(Filters=[ {'Name':'instance-type','Values':[instance_type]}, {'Name':'state', 'Values':['active']}, {'Name':'scope', 'Values':['Region']} ])
    return response['ReservedInstances']

def have_available_reserved_instances(region_name, instance_type, desired_instance_count):
    reserved_instances = find_available_reserved_instances(region_name, instance_type)
    available_instance_count = sum(map(lambda i: i['InstanceCount'], reserved_instances))
    return available_instance_count >= desired_instance_count



