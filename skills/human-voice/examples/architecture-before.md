# Rate Limiter for the Public API: Design Document

## Overview

This document proposes a new rate limiter for the public API. The limiter will protect backend services from traffic spikes, ensure fair usage across customers, and give the support team clearer information when a customer is throttled. It replaces the current per-instance token buckets with a shared limiter backed by Redis.

## Background

Today, each API instance keeps its own in-memory token bucket per API key. This worked well when the API ran on a small number of instances, but as the fleet has grown, the effective limit a customer sees has grown with it, since every instance grants its own allowance. Customers have noticed that their limits behave inconsistently, and the support team has struggled to explain throttling decisions.

## What is Rate Limiting?

In simple terms, rate limiting is a way of controlling how many requests a client can make in a given period of time. Think of it as a bouncer at a club who only lets a certain number of people in every minute. At its core, rate limiting is about protecting shared resources so that one busy client cannot crowd out everyone else.

## Design

Each request calls `EVALSHA` on a Lua script that implements a sliding-window counter in Redis. The key is `rl:{api_key}:{window_start}` with a 120-second TTL; the script reads the current and previous 60-second windows, weights the previous count by the fraction of the window that has elapsed, and increments the current window only if the weighted total is under the key's limit. Redis runs as a 3-shard cluster with one replica per shard, and keys hash on `{api_key}` so both windows for a key land on the same shard.

The limiter adds one Redis round trip per request. In a load test at 12,000 requests per second, p50 added latency was 0.4 ms and p99 was 1.9 ms. If Redis does not answer within 5 ms, the request is allowed and `ratelimit_redis_timeout_total` is incremented, so a Redis outage degrades to no limiting rather than to an API outage.

Throttled responses return `429` with `Retry-After` and `X-RateLimit-Remaining` headers, and the decision is logged with the key, the weighted count and the limit so support can answer tickets from the logs.

## Scalability

The new design is built to scale as usage continues to grow. Because the limiter state is shared, adding instances no longer changes the limits customers experience, which ensures consistent and predictable behavior. The Redis cluster can be expanded as needed to handle increased traffic, providing flexibility and reliability for the platform going forward. This approach allows the team to respond efficiently to changes in demand while maintaining a high level of performance for all customers. Over time, the shared design will also make it easier to introduce more sophisticated policies, giving the team valuable options as requirements evolve and ensuring that the limiter remains an effective and robust part of the overall architecture. Scalability has been a key consideration throughout the design process.

## Security

Access to Redis will be restricted.

## Testing

The limiter will be tested thoroughly.

## Rollout

We will roll this out gradually.

## Summary

In summary, this document proposes a shared rate limiter for the public API backed by Redis. The limiter protects backend services from traffic spikes, ensures fair usage across customers, and gives the support team clearer information when a customer is throttled. It replaces the per-instance token buckets, so limits no longer grow with the size of the fleet.
