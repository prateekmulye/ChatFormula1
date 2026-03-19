## 2024-05-24 - Throttling O(N) Cleanup Operations

**Learning:** Periodic O(N) cleanup operations (like cache eviction scans) that occur on read paths (e.g., inside `.get()`) can destroy O(1) performance guarantees under heavy load when the cache is nearly full.
**Action:** Always throttle such cleanup operations using a timestamp mechanism (e.g., run at most once per 60 seconds) to maintain consistent read performance while still ensuring eventual eviction.
