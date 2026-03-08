
## 2024-05-28 - Throttling Cache O(N) Sweeps
**Learning:** Checking for cache eviction during reads (`.get()`) without throttling can destroy O(1) performance when the cache nears its capacity. When the cache size is >90%, *every* `.get()` triggers an O(N) scan.
**Action:** Always throttle periodic cleanup operations that scan full collections on read paths (e.g., maintaining a `self._last_evict_time` to restrict execution frequency).
