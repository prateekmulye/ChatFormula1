## 2025-02-24 - Throttling Periodic Cache Sweeps
**Learning:** O(N) cache eviction sweeps triggered conditionally during read paths (like `.get()`) can destroy O(1) retrieval guarantees under heavy load when the cache stays near max capacity.
**Action:** Always throttle periodic cleanup operations on read paths using a timestamp mechanism (e.g., at most once per minute) to maintain O(1) read performance.
