# Migrating from REST to GraphQL

Run both. This is a layering job, not a rewrite, and the version that works has
GraphQL resolvers calling straight into the service layer your controllers already
use.

People come to GraphQL because of over-fetching. A mobile client wants three fields
off a user record and downloads the whole object; it wants data from four resources
and makes four trips. One request, described by the client, fixes that.

The complexity doesn't go anywhere, though. It moves. Query cost is unbounded until
you add depth limiting and complexity analysis. You lose the URL as a cache key,
which means persisted queries or a normalized client cache, neither of which is
free. And authorization goes into the resolvers field by field, which is more
thorough and also a lot more places to be wrong.

Sequence it this way. Read-only queries first, on one or two screens that get real
traffic. Leave mutations on REST until the query side is boring, because that is
where transactional semantics and error handling turn subtle. Instrument
resolver-level latency on day one; aggregate request time will tell you nothing
about which field is slow.

Do this when client teams are actually blocked by response shape. Not because the
API feels dated.
