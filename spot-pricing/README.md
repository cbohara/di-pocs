# Spot Pricing

For a given EC2 instance type and AWS region it does the following:

 * Get the demand price
 * Determine lowest spot price across availability zones for the given region
 * Determines if you should use spot pricing or not based on above items
 * Returns the availability zone for the lowest spot price and the bid price


## Potential future enhancements

### Volatility

  * This would be a measure of how much is the price likely to change
  * Instead of picking the lowest spot price the algorithm would pick the lowest spot price with the lowest volatility
  * One implementation would be to use the standard deviation of the spot price over a fixed time period
  * Another implemention would be to predict price increases using historical data and a machine learning algorithm (predict the price or predict whether the price will increase, or both)

### Instance types

  * [Spot instances with specific durations](https://aws.amazon.com/about-aws/whats-new/2015/10/introducing-amazon-ec2-spot-instances-for-specific-duration-workloads/)
  * Reserved instances
