## 2024-05-24 - Cache Eviction Throttling
**Learning:** O(N) cache eviction scans (like `_evict_expired`) triggered on read paths (e.g., `.get()`) block reads and destroy O(1) performance guarantees under heavy load.
**Action:** Throttle eviction scans on read paths using a timestamp mechanism (e.g., check every 60 seconds) rather than checking size on every request.
