## 2026-03-23 - O(N) Cache Eviction on Read Paths
**Learning:** O(N) cache eviction scans triggered on read paths (like `.get()`) can destroy O(1) performance guarantees under heavy load, blocking reads.
**Action:** Always throttle O(N) eviction scans on read paths using a timestamp mechanism to prevent performance degradation under load.
