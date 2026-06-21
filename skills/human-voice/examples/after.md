# Choosing a Data Infrastructure for Distributed Systems

Most teams pick their data infrastructure before they understand their access patterns. That order is backwards, and it costs them a rewrite a year later. This report works the other way: start from how your services actually read and write, then choose the architecture that fits.

## What to weigh

Three things decide the outcome, and they trade off against each other.

Performance and scalability usually pull in opposite directions. A system tuned for low single-query latency tends to shard poorly, so growth forces a redesign. If you expect traffic to 10x within a year, bias toward horizontal scaling now and accept a few extra milliseconds per query. If your load is flat, don't pay that tax.

Security is the constraint you cannot retrofit cheaply. Encryption at rest, row-level access control, and audit logging all shape the schema. Decide them first.

## A worked recommendation

For a service expecting rapid growth and handling regulated data, we recommend a partitioned Postgres cluster over a NoSQL store. The reason is concrete: you keep transactional guarantees and mature access-control tooling while still scaling writes through partitioning. NoSQL would scale further, but you would rebuild consistency and access control by hand, and for regulated data that is the wrong place to economize.

This recommendation has limits. We have not load-tested it past 50,000 writes per second, and it assumes a single region. Multi-region changes the calculus, and we would revisit the choice there.
