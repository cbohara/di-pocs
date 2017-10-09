import boto3
import datetime
import pytz
import urllib
import json
import sys
from decimal import Decimal
from awesome_print import ap


class PricingError(StandardError):
    pass


def get_instance_price(region_name, instance_type, offer_code, offer_code_filter):
    region_index_url = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{}/current/region_index.json".format(offer_code)
    response = urllib.urlopen(region_index_url)
    data = json.loads(response.read())

    if data['regions'].has_key(region_name):
        index_url = data['regions'][region_name]['currentVersionUrl']
        index_url = 'https://pricing.us-east-1.amazonaws.com' + index_url
    else:
        raise PricingError("Could not find pricing list for region '{}'".format(region_name))

    response = urllib.urlopen(index_url)
    data = json.loads(response.read())
    products = data['products'].values()
    products = filter(lambda product: product['attributes'].has_key('instanceType') and product['attributes']['instanceType'] == instance_type and offer_code_filter(product), products)

    if products:
        sku = products[0]['sku']
        print("sku: {}".format(sku))
        demand_price = data['terms']['OnDemand'][sku].values()[0]['priceDimensions'].values()[0]['pricePerUnit']['USD']
        return Decimal(demand_price)
    else:
        raise PricingError("Instance type '{}' is not available for use in EMR clusters".format(instance_type))


def get_ec2_instance_price(region_name, instance_type):
    return get_instance_price(region_name, instance_type, 'AmazonEC2', lambda product: product['attributes']['operatingSystem'] == 'Linux' and product['attributes']['tenancy'] == 'Shared')


def get_emr_instance_price(region_name, instance_type):
    return get_instance_price(region_name, instance_type, 'ElasticMapReduce', lambda product: product['attributes']['softwareType'] == 'EMR')


def get_lowest_spot_price(region_name, instance_type):
    ec2 = boto3.client('ec2', region_name=region_name)
    start_time = datetime.datetime.now(pytz.UTC) - datetime.timedelta(minutes=15)

    response = ec2.describe_availability_zones()
    availability_zones = response['AvailabilityZones']
    availability_zones = filter(lambda az: az['State'] == 'available', availability_zones)
    availability_zones = map(lambda az: az['ZoneName'], availability_zones)

    response = ec2.describe_spot_price_history(InstanceTypes=[instance_type], ProductDescriptions=['Linux/UNIX','Linux/UNIX (Amazon VPC)'], StartTime=start_time)
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
        raise PricingError("Could not find any spot price for instance type {0} in region {1}".format(instance_type,region_name))
    return lowest_spot_price


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("USAGE: python {} [aws-region] [ec2-instance-type]".format(sys.argv[0]))
        exit(1)

    region_name = sys.argv[1]
    instance_type = sys.argv[2]

    print("Region: {}".format(region_name))
    print("Instance Type: {}\n".format(instance_type))

    try:
        demand_price = get_ec2_instance_price(region_name, instance_type)
        print("Demand Price: {}\n".format(demand_price))

        lowest_spot_price = get_lowest_spot_price(region_name, instance_type)
        print("Lowest Spot Price: ")
        ap(lowest_spot_price)

        spot_price = lowest_spot_price['SpotPrice']
        availability_zone = lowest_spot_price['AvailabilityZone']

        if spot_price < demand_price:
            bid_price = "%.3f" % demand_price
            print("\nYou should use spot pricing with a bid price of ${0} in availability zone '{1}'\n".format(bid_price, availability_zone))
        else:
            print("\nYou should not use spot pricing\n")

    except PricingError as exception:
        print exception

