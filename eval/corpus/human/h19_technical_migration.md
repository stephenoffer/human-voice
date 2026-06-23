# Migrating off the shared Redis

We finally moved the rate limiter off the shared Redis cluster last week. It had been a problem for months. Every team's traffic hit the same instance, so one batch job in billing could spike memory and start evicting our limiter keys. When that happened, users got throttled who shouldn't have been.

The fix was not clever. We stood up a dedicated single-node Redis for the limiter, sized it at 4GB, and pointed only the gateway at it. No clustering, no replication yet. The limiter state is cheap to rebuild from scratch, so if the node dies we just fail open for a few seconds and refill.

That part scared people. It shouldn't have.

The tricky part was the cutover. We dual-wrote to both the old and new instances for three days, compared key counts hourly, and only flipped reads once the drift stayed under 0.1%. It never spiked.

One thing I'd do differently: we should have set a memory alarm on the new node before cutover, not after. We caught a slow leak two days in by luck, watching the dashboard during lunch. A page would have been better than a sandwich.
