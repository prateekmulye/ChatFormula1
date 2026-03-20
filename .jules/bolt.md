## 2024-05-24 - Throttle O(N) Cache Eviction Scans
**Learning:** O(N) cache eviction scans (like `_evict_expired`) triggered on a read path (`.get()`) without throttling can destroy O(1) performance guarantees under heavy load when the cache size remains above the threshold.
**Action:** Always throttle periodic O(N) cleanup operations on read paths using a timestamp mechanism (e.g., check if `time.time() - last_run > interval`) to prevent continuous blocking.
