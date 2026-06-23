<!-- Register: technical. Linter: before strong-tell (over_correction + internet_tells) -> after clean. -->
<!-- This is the BEFORE: the anti-AI costume — forced lowercase, sprinkled slang, staccato fragments, internet tells. -->

# the cache thing

ok so honestly? the cache was the problem. lowkey it always is. we shipped the new read path tuesday and idk, latency just... spiked. p99 went to like 900ms. straight up bad.

tbh nobody caught it in review. the eviction policy was load-bearing and we didn't know. the part no one tells you about lru is that under a hot-key burst it just thrashes. evicts the thing you need. fetches it again. evicts it again. chef's kiss.

so we sat down friday. dug through the traces. the keys were fine, the ttl was fine, the size was the issue lol. cache too small. 200mb. for that workload? no notes, it was never gonna hold.

we bumped it to 2gb and added a small admission filter so cold keys don't evict hot ones. p99 dropped back to 80ms. this hits different ngl. shipped the fix saturday. monitoring's been quiet since. that's growth i guess.
