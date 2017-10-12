import mock
import unittest
from ec2.pricing import Pricing, PricingError

class PricingTest(unittest.TestCase):

    def test_success(self):
        pricing = Pricing(region_name='us-east-1', instance_type='r3.2xlarge')
        self.assertTrue(pricing.lowest_spot_price['SpotPrice'] > 0)
        self.assertTrue('us-east-1' in pricing.lowest_spot_price['AvailabilityZone'])
        self.assertEqual('r3.2xlarge', pricing.lowest_spot_price['InstanceType'])
        self.assertTrue(pricing.demand_price > 0)
        self.assertTrue(str(pricing.bid_price) in "${}".format(pricing.demand_price))

    def test_invalid_region(self):
        try:
            pricing = Pricing(region_name='us-north-1', instance_type='r3.2xlarge')
        except PricingError, pe:
            self.assertTrue('Invalid region name' in str(pe))

    def test_invalid_instance_type(self):
        try:
            region_name, instance_type = 'us-east-1', 'x100.100xlarge'
            pricing = Pricing(region_name=region_name, instance_type=instance_type)
        except PricingError, pe:
            self.assertEqual("Instance type {0} is not available for use in AmazonEC2".format(instance_type), str(pe))

    @mock.patch('ec2.pricing.urllib.urlopen', autospec=True)
    def test_price_list_not_found(self, urlopen):
        urlopen.return_value.read.return_value = '{"regions": {"us-west-1": null, "us-west-2": null} }'

        try:
            pricing = Pricing(region_name='us-east-1', instance_type='r3.2xlarge')
        except PricingError, pe:
            self.assertTrue('Could not find pricing list for region' in str(pe))

if __name__ == '__main__':
   unittest.main()