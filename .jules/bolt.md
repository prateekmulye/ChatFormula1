## 2026-04-10 - O(N) Scan on Cache Reads
**Learning:** Found an anti-pattern in the custom `TTLCache` where an O(N) full scan of expired elements (`_evict_expired()`) was being triggered synchronously on every `get()` call whenever the cache hit 90% capacity. This led to disastrous scaling when the cache was heavily utilized, completely blocking O(1) reads.
**Action:** Always verify that background cleanup tasks like evictions on reads are appropriately throttled (e.g., using time-based limits) to avoid degrading fast-path operations.
