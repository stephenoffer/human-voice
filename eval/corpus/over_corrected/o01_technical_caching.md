ok so the caching layer. honestly? it's giving better tail latency, fr.

we put a read-through cache in front of postgres. idk why we waited so long tbh. the hit rate sits around 92 percent after warmup. that's growth.

eviction is LRU with a 30 minute TTL. simple. boring. it works.

the part no one tells you: cache invalidation on writes is the load-bearing piece. miss it and you serve stale rows for an hour, lol.

ngl the metrics dashboard hits different now. p99 dropped from 400ms to 60ms. no notes.

deploy is behind a feature flag. roll it to 5 percent first. watch the error rate. then ramp.

one gotcha. cold starts after a deploy flush everything. expect a latency spike for maybe two minutes. smh. it settles.
