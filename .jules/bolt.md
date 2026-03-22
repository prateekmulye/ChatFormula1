## 2024-03-22 - Throttled O(n) Cache Eviction Scans
**Learning:** O(n) cache eviction scans blocking read paths (like `_evict_expired()` in `get()`) without throttling can cause significant latency issues under heavy load.
**Action:** Always implement a timestamp mechanism to throttle expensive O(n) scans triggered on read paths, ensuring O(1) performance guarantees are maintained.
