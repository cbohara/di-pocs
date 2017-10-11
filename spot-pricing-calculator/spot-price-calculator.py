import boto3
import datetime
import pytz
import urllib
import json
import sys
from decimal import Decimal
from awesome_print import ap
from ec2.pricing import EC2InstancePrice, EC2InstancePriceError

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("USAGE: python {} [aws-region] [ec2-instance-type]".format(sys.argv[0]))
        exit(1)

    region_name = sys.argv[1]
    instance_type = sys.argv[2]

    print("Region: {}".format(region_name))
    print("Instance Type: {}\n".format(instance_type))

    try:
        price = EC2InstancePrice(region_name=region_name, instance_type=instance_type)

        demand_price = price.demand_price
        print("Demand Price: {}\n".format(demand_price))

        lowest_spot_price = price.lowest_spot_price
        print("Lowest Spot Price: ")
        ap(lowest_spot_price)

        spot_price = lowest_spot_price['SpotPrice']
        availability_zone = lowest_spot_price['AvailabilityZone']

        if spot_price < demand_price:
            bid_price = "%.3f" % demand_price
            print("\nYou should use spot pricing with a bid price of ${0} in availability zone '{1}'\n".format(bid_price, availability_zone))
        else:
            print("\nYou should not use spot pricing\n")

    except EC2InstancePriceError as exception:
        print exception

