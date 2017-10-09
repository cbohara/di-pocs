import boto3
import datetime
import pytz
import urllib
import json
import sys
from decimal import Decimal
from awesome_print import ap

class EMRInstancePriceError(StandardError):
    pass

class EMRInstancePrice(object):
    pricing_url = 'https://pricing.us-east-1.amazonaws.com'

    def __init__(self, region_name, instance_type):
        self.region_name = region_name
        self.instance_type = instance_type
        ec2 = boto3.client('ec2')
        response = ec2.describe_regions()
        regions_names = map(lambda region: region['RegionName'], response['Regions'])
        if not any(region_name == valid_region for valid_region in regions_names):
            raise EMRInstancePriceError("Invalid region name '{}'".format(region_name))

    @property
    def demand_price(self):
        region_index_url = self.pricing_url + "/offers/v1.0/aws/ElasticMapReduce/current/region_index.json"
        response = urllib.urlopen(region_index_url)    
        data = json.loads(response.read())

        if data['regions'].has_key(self.region_name):
            index_url = data['regions'][self.region_name]['currentVersionUrl']
            index_url = self.pricing_url + index_url
        else:
            raise EMRInstancePriceError("Could not find pricing list for region '{}'".format(self.region_name))

        response = urllib.urlopen(index_url)
        data = json.loads(response.read())
        products = data['products'].values()
        products = filter(lambda product: product['attributes']['instanceType'] == self.instance_type and product['attributes']['softwareType'] == 'EMR', products)

        if products:
            sku = products[0]['sku']
            demand_price = data['terms']['OnDemand'][sku].values()[0]['priceDimensions'].values()[0]['pricePerUnit']['USD']
            return Decimal(demand_price)
        else:
            raise EMRInstancePriceError("Instance type '{}' is not available for use in EMR clusters".format(self.instance_type))


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
            raise EMRInstancePriceError("Could not find any spot price for instance type {0} in region {1}".format(self.instance_type,region_name))
        return lowest_spot_price


# from emr.pricing import EMRInstancePrice, EMRInstancePriceError
# price = EMRInstancePrice(region_name='us-west-1',instance_type='r3.2xlarge')

