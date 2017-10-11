import boto3
import datetime
import pytz
import urllib
import json
import sys
from decimal import Decimal
from awesome_print import ap
from ec2.pricing import Pricing, PricingError


if len(sys.argv) < 3:
   print("USAGE: python {} [aws-region] [ec2-instance-type]".format(sys.argv[0]))
   sys.exit(1)

region_name = sys.argv[1]
instance_type = sys.argv[2]

print("Region: {}".format(region_name))
print("Instance Type: {}\n".format(instance_type))

try:
   pricing = Pricing(region_name=region_name, instance_type=instance_type)

   print("Demand Price: {}\n".format(pricing.demand_price))

   print("Lowest Spot Price: ")
   ap(pricing.lowest_spot_price)

   if pricing.should_use_spot_price():
      print("\nYou should use spot pricing with a bid price of ${0} in availability zone '{1}'\n".format(pricing.bid_price, pricing.availability_zone))
   else:
      print("\nYou should not use spot pricing\n")

except PricingError as exception:
   print exception