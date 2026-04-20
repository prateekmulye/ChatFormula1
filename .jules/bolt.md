## 2026-04-20 - TTLCache Eviction Bottleneck
**Learning:** O(N) background cache eviction logic triggered during a `.get()` operation caused severe performance degradation when the cache was near capacity, effectively making the cache O(N) for reads instead of O(1).
**Action:** Always throttle O(N) background maintenance tasks on the read path of caching structures using a timestamp check.
