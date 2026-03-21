## 2026-03-21 - Throttling O(N) Cache Evictions on Read Paths
**Learning:** Calling O(N) cache eviction scans (`_evict_expired`) during cache read operations (`.get()`) without any throttling completely destroys O(1) performance guarantees precisely when the system needs them most (when the cache is mostly full and heavily queried).
**Action:** Always implement a timestamp-based or counter-based throttle to limit how frequently expensive eviction scans run on read paths, ensuring reads remain O(1) on average.
