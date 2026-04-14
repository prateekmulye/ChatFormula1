## 2024-04-14 - Cache Eviction Throttling

**Learning:** `TTLCache.get()` has an O(N) background eviction scan (`_evict_expired`) that was being triggered on every cache read path when the cache was near full (>90% utilization). This creates a severe performance bottleneck during high traffic since read operations (get) should be O(1) but were degraded to O(N).
**Action:** Implemented a timestamp-based throttling mechanism (`self._last_evict_time`) to ensure the O(N) scan only runs periodically (e.g., at most once per minute), restoring O(1) performance to the read path while still maintaining bounds on cache size.
