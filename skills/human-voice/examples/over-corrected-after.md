<!-- Register: technical (postmortem). Before: strong-tell (over_correction + -->
<!-- internet_tells). After: clean -- and in a lived-in on-call voice, distinct -->
<!-- from the crisp report cadence of after.md, so the example set isn't all one -->
<!-- "confident tech-blog" register. No slang, no "second dialect" tics. -->

# The cache outage

This one was the cache, though it took us four days to believe it.

We shipped the new read path Tuesday morning, and by noon p99 had climbed from 80ms to 900ms. Review missed it because the bug wasn't really in the diff. The eviction policy was quietly doing far more work than the change suggested. When hot-key traffic spiked, the LRU store began to thrash: it evicted the key we had just asked for, fetched it again, then dropped it once more on the next request. Most of the cache capacity went to that churn instead of serving reads.

When we finally traced it on Friday, the cause turned out to be almost dull. The keys were right. So were the TTLs. The working-set size was the problem: at 200MB the set never fit, so any hot key sat one cold request from eviction.

Two changes fixed it. We raised the cap to 2GB, then added an admission filter so a single cold key can no longer evict a hot one. p99 settled back to 80ms and stayed there. We shipped Saturday, and the graphs have been quiet since, which after a week like that was all we wanted.
