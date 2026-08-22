# Choosing a queue for the notification service

We're using the Postgres job table. Not SQS, not Redis Streams.

Throughput was never the axis. Operational cost was, and that surprised us.

Redis Streams wins on speed by a wide margin: single-digit milliseconds under our
test load, against forty at the median for Postgres. But Redis is not in our
stack today. Adding it means a second stateful system, with its own failure modes
and its own page at 3 a.m. No benchmark shows you that number.

SQS is managed, so the operational argument runs the other way. It died on the
256KB message limit. Our notification payloads routinely exceed it, which forces
a claim-check against S3, and the claim-check indirection lands squarely in the
consumer, where we least want it.

So: Postgres. It is the slowest of the three and it needs no new infrastructure.
Transactional enqueue comes free. Backups and monitoring already exist. And
notification delivery is a background job nobody waits on, so forty milliseconds
buys us a system we already know how to operate.

Queue benchmarks are the easiest part of this decision and the least important
one. We picked the boring option on purpose.
