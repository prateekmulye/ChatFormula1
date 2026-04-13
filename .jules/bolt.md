## 2026-04-13 - Throttling O(N) eviction scans in TTLCache
**Learning:** The TTLCache in `src/utils/cache.py` utilized a background eviction scan O(N) over `_cache.items()` in `_evict_expired()` when `len(self._cache) > self.max_size * 0.9`. This executed on every `get()` call, blocking O(1) read paths during high cache utilization.
**Action:** Implement a timestamp-based throttling mechanism (`self._last_evict_time`) to prevent O(N) scans from executing more than once every 60 seconds.
