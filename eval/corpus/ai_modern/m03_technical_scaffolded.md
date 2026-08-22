# Migrating from REST to GraphQL

Moving an established REST API to GraphQL is less a rewrite than a gradual layering exercise. The pattern that works best in practice is to run both in parallel, with GraphQL resolvers calling into the same service layer your REST controllers already use.

## Why teams make the switch

The usual motivation is over-fetching. A mobile client that needs three fields from a user record ends up downloading the whole object, and clients that need data from four resources make four round trips. GraphQL lets the client describe exactly what it wants in a single request.

## Where the complexity moves

The complexity does not disappear; it relocates. Query cost becomes unbounded unless you add depth limiting and complexity analysis. Caching gets harder because you lose the URL as a cache key, so you need either persisted queries or a normalized client cache. Authorization has to move into the resolver layer, field by field, which is more thorough but also more places to get it wrong.

## A reasonable sequence

Start with read-only queries for one or two high-traffic screens. Keep mutations on REST until the query side is stable, since mutations are where transactional semantics and error handling get subtle. Instrument resolver-level latency from day one, because the aggregate request time tells you nothing about which field is slow.

The migration is worth doing when client teams are genuinely blocked by response shape, and not worth doing because the API feels dated.
