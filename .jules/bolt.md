## 2024-05-15 - O(N) Cache Eviction Blocking O(1) Reads
**Learning:** O(N) cache eviction scans trigger on every O(1) read operation (`get`) when cache size exceeds a threshold, severely blocking read paths during high utilization.
**Action:** Use a timestamp-based throttling mechanism (`self._last_evict_time`) to limit the frequency of background eviction scans and preserve O(1) read performance.
