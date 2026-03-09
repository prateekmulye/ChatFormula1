## 2026-03-09 - Throttle O(N) cache eviction scans
**Learning:** In heavily used caching systems like `TTLCache`, naive length-based eviction triggers (e.g. `if len(cache) > max_size * 0.9: evict()`) can cause O(N) periodic sweeps to execute on *every single read operation* once the cache is near capacity. This drastically degrades O(1) read performance to O(N).
**Action:** Always implement a time-based throttle (e.g. at most once per second using a timestamp) for background O(N) cleanup tasks that reside on hot read paths.
