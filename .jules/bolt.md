## 2026-04-01 - O(N) Cache Eviction Scans on Read Paths
**Learning:** To avoid blocking reads and destroying O(1) performance guarantees under heavy load, O(N) cache eviction scans (like `_evict_expired` in `src/utils/cache.py`) triggered on read paths (e.g., `.get()`) must be throttled using a timestamp mechanism. A full dictionary scan on every `.get()` request when the cache is 90% full reduces performance significantly.
**Action:** Always throttle O(N) background cleanup operations on hot read paths. Used a 60-second minimum interval between full cache scans.
