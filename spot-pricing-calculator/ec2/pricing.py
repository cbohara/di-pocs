import boto3
import datetime
import pytz
import urllib
import json
import sys
from decimal import Decimal
from awesome_print import ap

class EC2InstancePriceError(StandardError):
    pass

class EC2InstancePrice(object):
    pricing_url = 'https://pricing.us-east-1.amazonaws.com'

    def __init__(self, region_name, instance_type):
        self.region_name = region_name
        self.instance_type = instance_type
        ec2 = boto3.client('ec2')
        response = ec2.describe_regions()
        regions_names = map(lambda region: region['RegionName'], response['Regions'])
        if not any(region_name == valid_region for valid_region in regions_names):
            raise EC2InstancePriceError("Invalid region name '{}'".format(region_name))

    @property
    def demand_price(self):
        return self.ec2_instant_price()

    def instance_price(self, offer_code, offer_code_filter):
        region_index_url = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{}/current/region_index.json".format(offer_code)
        response = urllib.urlopen(region_index_url)
        data = json.loads(response.read())

        if data['regions'].has_key(self.region_name):
            index_url = data['regions'][self.region_name]['currentVersionUrl']
            index_url = 'https://pricing.us-east-1.amazonaws.com' + index_url
        else:
            raise PricingError("Could not find pricing list for region '{}'".format(region_name))

        response = urllib.urlopen(index_url)
        data = json.loads(response.read())
        products = data['products'].values()
        products = filter(lambda product: product['attributes'].has_key('instanceType') and product['attributes']['instanceType'] == self.instance_type and offer_code_filter(product), products)

        if products:
            sku = products[0]['sku']
            print("sku: {}".format(sku))
            demand_price = data['terms']['OnDemand'][sku].values()[0]['priceDimensions'].values()[0]['pricePerUnit']['USD']
            return Decimal(demand_price)
        else:
            raise PricingError("Instance type '{}' is not available for use in EMR clusters".format(self.instance_type))

    def ec2_instant_price(self):
        return self.instance_price('AmazonEC2', lambda product: product['attributes']['operatingSystem'] == 'Linux' and product['attributes']['tenancy'] == 'Shared')

    def emr_instance_price(self):
        return self.instance_price('ElasticMapReduce', lambda product: product['attributes']['softwareType'] == 'EMR')

    @property
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
            recent_spot_prices = filter(lambda price: price['AvailabilityZone'] == availability_zone and price['Timestamp'] >= start_time, instance_spot_prices)
            if recent_spot_prices:
                spot_prices_sorted_by_time = sorted(recent_spot_prices, key=lambda price: price['Timestamp'])
                latest_spot_price = spot_prices_sorted_by_time[-1]
                latest_spot_price['SpotPrice'] = Decimal(latest_spot_price['SpotPrice'])
                latest_spot_prices.append(latest_spot_price)

        if latest_spot_prices:
            lowest_spot_price = min(latest_spot_prices, key=lambda price: price['SpotPrice'])
        else:
            raise EC2InstancePriceError("Could not find any spot price for instance type {0} in region {1}".format(self.instance_type,region_name))
        return lowest_spot_price

    @property
    def bid_price(self):
        return "%.3f" % self.demand_price

    def should_use_spot_price():
        pass


