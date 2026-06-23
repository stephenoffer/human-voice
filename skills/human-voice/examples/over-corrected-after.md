<!-- Register: technical. Linter: before strong-tell (over_correction + internet_tells) -> after clean. -->
<!-- This is the AFTER: a real, plain voice. Normal capitalization, committed -->
<!-- stance, varied rhythm, no slang. Also no "second dialect": the ", and" -->
<!-- splice rhythm is broken up and the "X is Y" copulas are varied. -->

# The cache outage

The cache caused it. We shipped the new read path on Tuesday. Within the hour, p99 latency jumped from 80ms to 900ms.

Nobody caught it in review, for a specific reason: the eviction policy did more work than anyone realized. Under a burst of hot-key traffic, the LRU store thrashed. It would evict the key we needed, refetch it, then drop it again on the very next request. Capacity went to churn instead of serving reads.

We traced it on Friday. The keys checked out. So did the TTLs. What we had wrong was the size. A 200MB working set never fit, so every hot key sat one cold request away from eviction.

Fixing it took two changes. First we raised the limit to 2GB. Then we added an admission filter so a single cold key can no longer evict a hot one. P99 dropped back to 80ms and held there. We shipped Saturday. The dashboards have been quiet since.
