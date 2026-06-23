# Choosing a Data Infrastructure for Distributed Systems

Most teams pick their data infrastructure before they understand how their services read and write. That's backwards. The bill comes due a year later, as a rewrite. So flip the order: learn the access patterns first, then pick the architecture that fits them.

## What to weigh

Two forces decide the outcome, and they tend to fight each other.

Performance and scalability usually pull in opposite directions. Tune a system for low single-query latency and it shards poorly, so growth forces a redesign. Expect traffic to 10x within a year? Bias toward horizontal scaling now; accept a few extra milliseconds per query. If your load is flat, don't pay that tax.

Then there is security, the one constraint you cannot retrofit cheaply. It shapes the schema from the first table you draw. Encryption at rest changes your column types; row-level access control changes your foreign keys. Decide both before you commit a migration.

## A worked recommendation

For a service expecting rapid growth and handling regulated data, we recommend a partitioned Postgres cluster over a NoSQL store. The reasoning is concrete. You keep transactional guarantees and mature access-control tooling while still scaling writes through partitioning. NoSQL would scale further, but then you rebuild consistency and access control by hand. For regulated data, that is the wrong corner to cut.

This recommendation has limits. We have not load-tested it past 50,000 writes per second. It also assumes a single region. Multi-region changes the calculus enough that we would revisit the choice there.
