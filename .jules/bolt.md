## 2024-04-17 - Throttle TTL Cache Eviction
**Learning:** In the `TTLCache` in `src/utils/cache.py`, a timestamp-based throttling mechanism (`self._last_evict_time`) is needed to prevent O(N) background eviction scans from blocking O(1) read paths (`get()`) during high cache utilization.
**Action:** Always throttle periodic cleanup operations inside frequently called read paths.
