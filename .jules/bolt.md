## 2024-03-26 - Throttling O(N) Cache Eviction Scans on Read Paths
**Learning:** In `src/utils/cache.py`, the `_evict_expired` method performs an O(N) scan of the cache. When triggered on the `.get()` read path solely based on cache capacity (`> 90%`), it can run on every single read under heavy load if the cache remains full but unexpired, destroying O(1) read performance guarantees.
**Action:** Always throttle O(N) maintenance operations on read paths using a timestamp mechanism (e.g., limit execution to once per 60 seconds) to preserve O(1) read latency.
