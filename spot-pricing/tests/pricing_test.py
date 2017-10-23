import mock
import unittest
from vrvm_new.pricing import Pricing, PricingError

class PricingTest(unittest.TestCase):

    def test_success(self):
        pricing = Pricing(region_name='us-east-1', instance_type='r3.2xlarge')
        self.assertTrue(pricing.lowest_spot_price['SpotPrice'] > 0)
        self.assertTrue('us-east-1' in pricing.lowest_spot_price['AvailabilityZone'])
        self.assertEqual('r3.2xlarge', pricing.lowest_spot_price['InstanceType'])
        self.assertTrue(pricing.demand_price > 0)
        self.assertTrue(str(pricing.bid_price) in "${}".format(pricing.demand_price))

    def test_invalid_instance_type_demand_price(self):
        region_name, instance_type = 'us-east-1', 'x100.100xlarge'
        with self.assertRaisesRegexp(PricingError, "Instance type {0} is not available for use in AmazonEC2".format(instance_type)):
            pricing = Pricing(region_name=region_name, instance_type=instance_type)
            pricing.demand_price

    def test_invalid_instance_type_spot_price(self):
        region_name, instance_type = 'us-east-1', 'x100.100xlarge'
        with self.assertRaisesRegexp(PricingError, "Could not find any spot price for instance type {0} in region {1}".format(instance_type, region_name)):
            pricing = Pricing(region_name=region_name, instance_type=instance_type)
            pricing.lowest_spot_price

    @mock.patch('vrvm_new.pricing.urllib.urlopen', autospec=True)
    def test_price_list_not_found(self, urlopen):
        urlopen.return_value.read.return_value = '{"regions": {"us-west-1": null, "us-west-2": null} }'
        with self.assertRaisesRegexp(PricingError, 'Could not find pricing list for region'):
            pricing = Pricing(region_name='us-east-1', instance_type='r3.2xlarge')
            pricing.demand_price

if __name__ == '__main__':
    unittest.main()