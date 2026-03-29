## 2024-03-29 - O(1) Performance Guarantee Destruction in Cache Reads
**Learning:** O(N) cache eviction scans (like `_evict_expired`) triggered on read paths (e.g., `.get()`) can destroy O(1) performance guarantees under heavy load, as they block all concurrent reads when the cache is nearly full.
**Action:** Always throttle O(N) cleanup operations on read paths using a timestamp mechanism (e.g., at most once per 60 seconds) to preserve O(1) read latency.
