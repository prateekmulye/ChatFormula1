
## 2026-03-05 - TTL Cache Eviction Throttling
**Learning:** Checking for cache evictions on every `get()` call when a TTL cache is near capacity turns amortized O(1) cache lookups into O(N) operations, creating a severe performance bottleneck under load. Additionally, calling `time.time()` inside an O(N) list comprehension adds significant overhead.
**Action:** Throttle full-cache eviction scans (e.g., to once per second) by tracking the last eviction time. When performing O(N) timestamp comparisons, cache `time.time()` into a local variable before the loop instead of invoking it repeatedly.
