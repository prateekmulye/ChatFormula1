## 2024-04-09 - TTLCache Get Throttling
**Learning:** During high cache utilization, checking if a cache needs cleanup based on a condition like `len(cache) > 0.9 * max_size` on every `get` call leads to O(N) background eviction scans that block the O(1) read path.
**Action:** Throttle the background eviction scan using a timestamp (e.g. `self._last_evict_time`) to ensure it runs at most once every interval (e.g., 60 seconds), keeping reads fast and predictable.
