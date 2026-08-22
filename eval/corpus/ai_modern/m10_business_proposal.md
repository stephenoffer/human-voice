# Proposal: consolidate the three support queues

We currently route support requests through three separate systems, one for each product line. This made sense when the products were sold to different buyers. It no longer does, because roughly a third of our accounts now use two or more products and their requests get bounced between queues.

The consolidation would move all three onto the platform the largest team already uses, with product as a routing tag rather than a separate instance. The direct savings are modest, around eighteen thousand a year in licensing. The real benefit is that a single ticket can cover two products without a handoff, which is where our slowest resolutions currently come from.

The main cost is migration effort. Two teams have built reporting on top of their existing instance and those reports would need rebuilding, which we estimate at three weeks of one engineer's time. There is also a training cost that is easy to underestimate, since agents develop muscle memory for their tooling.

I recommend proceeding, with the migration scheduled after the busy season rather than before it. The savings argument alone would not justify the disruption, but the cross-product handoff problem is growing with the account mix, and it will be more expensive to fix later.
