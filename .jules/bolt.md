## 2025-02-24 - Throttling O(N) Cache Eviction Scans
**Learning:** Triggering O(N) cache eviction scans unconditionally on size thresholds inside `get()` will silently destroy O(1) read performance under high load.
**Action:** Always implement a timestamp-based throttling mechanism (`_last_evict_time`) for expensive background maintenance tasks that intercept frequent execution paths.
