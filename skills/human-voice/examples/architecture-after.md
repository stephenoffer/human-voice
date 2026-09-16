# Rate limiter for the public API

Customer rate limits currently grow with the fleet. Each API instance keeps its own token bucket per API key. That worked on a handful of instances, but every instance we add hands each customer another allowance. Customers have noticed their limits behave inconsistently, and support has struggled to explain throttling decisions.

This proposal replaces the per-instance buckets with one sliding-window counter per key in Redis. The limit then holds at any fleet size. That protects the backends from spikes and keeps one busy key from crowding out the rest. A shared counter should also make richer policies easier to add later.

## How a request is counted

Each request runs a Lua script through `EVALSHA`. The script reads the current and previous 60-second windows for the key, weights the previous count by how much of the current window has elapsed, and increments only if the weighted total is under the limit. Keys look like `rl:{api_key}:{window_start}` with a 120-second TTL. The `{api_key}` hash tag keeps both windows on one shard of the 3-shard cluster (one replica per shard).

A throttled request gets a `429` with `Retry-After` and `X-RateLimit-Remaining`. The log line records the key, the weighted count and the limit, which is what support needs to answer a ticket.

## Cost and failure

One Redis round trip per request. At 12,000 requests per second in the load test that added 0.4 ms at p50 and 1.9 ms at p99. The cluster can be expanded as traffic grows.

If Redis takes longer than 5 ms, the request goes through and `ratelimit_redis_timeout_total` goes up. A Redis outage therefore turns limiting off. It does not take the API down with it.

That tradeoff is deliberate. It is also the one reviewers should push on.

Three commitments have no detail behind them yet. Access to Redis will be restricted. The limiter will be tested. Rollout will be gradual. This document doesn't yet say how for any of them. [OWNER NEEDED]
