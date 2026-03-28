## 2024-03-28 - Avoid O(N) Cache Eviction Scans on Read Paths
**Learning:** Naive cache eviction scans (like `_evict_expired` running an O(N) scan over all cache items) triggered on `.get()` calls destroy O(1) read performance under heavy load when the cache nears its max size.
**Action:** Always throttle O(N) eviction scans triggered on read paths (e.g., using a timestamp mechanism like checking if `current_time - last_evict_time > 60.0`) to ensure O(1) performance guarantees are preserved under load.
