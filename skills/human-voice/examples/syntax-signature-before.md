# Choosing a queue for the notification service

We evaluated three options for the notification service: SQS, Redis Streams, and
a Postgres-backed job table. What ultimately decided it was operational cost
rather than throughput, which was not the axis we expected to matter.

Redis Streams is the fastest of the three by a wide margin, delivering messages
in single-digit milliseconds under our test load. The problem is that Redis is
not currently part of our stack, meaning we would be adding a second stateful
system with its own failure modes and its own on-call burden. What that costs is
not visible in a benchmark.

SQS is managed, removing the operational burden entirely. The reason we did not
choose it is that our notification payloads routinely exceed the 256KB message
limit, requiring a claim-check pattern against S3, and it is the claim-check
indirection that would have added the most complexity to the consumer.

The Postgres job table is the slowest option, adding roughly forty milliseconds
of latency at the median. It is also the only option that requires no new
infrastructure, giving us transactional enqueue for free and letting us reuse the
backup and monitoring we already run. What matters here is that notification
delivery is not latency-sensitive, and it is a background job that a user never
waits on.

The thing about queue selection is that the benchmark numbers are the easiest
part of the decision and the least important. We are going with Postgres, and it
is the boring choice, and it is the right one.
