## 2024-04-07 - TTLCache Get Performance Degradation

**Learning:** `src/utils/cache.py` implements a `TTLCache` where the `get()` method performs a linear scan to clean up expired entries when the cache is over 90% capacity (`if len(self._cache) > self.max_size * 0.9`). This turns a theoretically O(1) operation into an O(N) operation during peak load. In our test with 95,000 items, `get()` took ~43ms per call on average, which is catastrophic for a caching layer.

**Action:** We need to throttle background evictions in the read path. Instead of running `_evict_expired()` on every single `get()` when the cache is full, we should track when the last eviction occurred and only run it periodically (e.g. at most once per minute). This preserves O(1) read performance while still maintaining memory bounds.
