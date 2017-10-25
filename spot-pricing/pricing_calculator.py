import boto3
import datetime
import pytz
import urllib
import json
import sys
from decimal import Decimal
from awesome_print import ap
from vrvm_new.pricing import Pricing, PricingError, find_available_reserved_instances


if len(sys.argv) < 4:
   print("USAGE: python {} [aws-region] [ec2-instance-type] [instance-count]".format(sys.argv[0]))
   sys.exit(1)

region_name = sys.argv[1]
instance_type = sys.argv[2]
instance_count = int(sys.argv[3])

print("Region: {}".format(region_name))
print("Instance Type: {}".format(instance_type))
print("Instance Count: {}\n".format(instance_count))

try:
   pricing = Pricing(region_name=region_name, instance_type=instance_type)

   print("Demand Price: {}\n".format(pricing.demand_price))

   reserved_instances = find_available_reserved_instances(region_name=region_name, instance_type=instance_type)
   reserved_instances_count = sum(map(lambda i: i['InstanceCount'], reserved_instances))
   print("Reserved Instances Available: {}\n".format(reserved_instances_count))

   print("Lowest Spot Price: ")
   ap(pricing.lowest_spot_price)

   if reserved_instances_count >= instance_count:
      print("\nYou should not use spot pricing. There are enough reserved instances.\n")
   else:
      if pricing.should_use_spot_price():
         print("\nYou should use spot pricing with a bid price of ${0} in availability zone '{1}'\n".format(pricing.bid_price, pricing.availability_zone))
      else:
         print("\nYou should not use spot pricing. The spot price is higher than the demand price.\n")

except PricingError as exception:
   print exception