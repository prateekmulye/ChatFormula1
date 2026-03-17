
## 2024-05-24 - Cache Eviction Read Path Bottleneck
**Learning:** O(N) cache eviction scans (`_evict_expired`) triggered automatically inside `.get()` methods can completely destroy the expected O(1) performance guarantees of the cache when under heavy load and near max capacity.
**Action:** Always throttle periodic O(N) cleanup operations on read paths using a timestamp mechanism (like `time.time() - self._last_evict_time > 60`) to maintain fast average read latency.
