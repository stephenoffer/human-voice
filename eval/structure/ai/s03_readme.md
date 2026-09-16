# fastcache

A high-performance, in-process LRU cache for Python services with TTL support and async-safe locking.

## What is a cache?

Before we dive in, a quick primer. In simple terms, a cache is a place where you store the results of expensive work so you don't have to do it again. Think of it as a notebook where you jot down answers you've already figured out. The next time someone asks the same question, you just look in the notebook instead of working it out from scratch.

Caches are everywhere in computing. Your web browser uses one, your operating system uses one, and even your CPU uses several. At its core, caching is about trading memory for speed.

## Installation

```bash
pip install fastcache-lru==2.3.1
```

Requires Python 3.9+ and has no runtime dependencies.

## Usage

```python
from fastcache import LRUCache

cache = LRUCache(maxsize=10_000, ttl=300)

@cache.memoize(key=lambda user_id: f"user:{user_id}")
async def load_user(user_id: int) -> dict:
    return await db.fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

`maxsize` bounds the number of entries; eviction is O(1) using an intrusive doubly linked list. `ttl` is checked lazily on `get()` and eagerly by a background sweeper every `sweep_interval` seconds (default 30). Set `ttl=None` to disable expiry.

## Performance

Benchmarked on an M2 Pro, Python 3.12, 1M operations, 90/10 read/write mix, `maxsize=100_000`:

| Library | get p50 | get p99 | set p99 | RSS |
|---|---|---|---|---|
| fastcache 2.3 | 88 ns | 190 ns | 410 ns | 61 MB |
| cachetools 5.3 | 240 ns | 610 ns | 1.2 µs | 74 MB |
| functools.lru_cache | 71 ns | 150 ns | n/a | 58 MB |

Under contention with 32 asyncio tasks, `AsyncLRUCache` holds p99 `get` under 1.1 µs because it uses a single `asyncio.Lock` per shard (16 shards by default, configurable via `shards=`).

## Why caching matters

Simply put, caching makes your application faster. Imagine you have a function that takes a whole second to run. If you call it a hundred times, that's a hundred seconds. With a cache, you only pay that cost once. In plain English, a cache helps your users wait less and helps your servers do less work.

## Configuration

| Option | Default | Description |
|---|---|---|
| `maxsize` | 1024 | Maximum entries before LRU eviction |
| `ttl` | `None` | Seconds until an entry expires |
| `shards` | 16 | Lock shards for `AsyncLRUCache` |
| `sweep_interval` | 30 | Background expiry sweep period |
| `on_evict` | `None` | Callback `(key, value) -> None` |

## License

MIT
