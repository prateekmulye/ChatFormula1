## 2024-04-05 - O(N) cache eviction blocking O(1) read paths
**Learning:** Using `len(cache) > limit` to trigger O(N) background eviction scans directly in the O(1) `get()` path causes severe performance degradation when the cache operates near capacity.
**Action:** Introduce a timestamp-based throttling mechanism (e.g., `_last_evict_time`) to ensure expensive eviction sweeps occur at most once per second during high utilization, preserving the O(1) read path performance.
