## 2024-04-03 - TTLCache read path degradation
**Learning:** Checking for expired entries periodically in a cache's `get` path can inadvertently turn O(1) reads into O(N) operations when the cache is nearly full, as the threshold condition will trigger on every request.
**Action:** Always implement a timestamp-based throttling mechanism (like `_last_evict_time`) for background O(N) maintenance tasks triggered by frequent O(1) read paths.
