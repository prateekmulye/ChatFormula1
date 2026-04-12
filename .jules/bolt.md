## 2024-04-12 - TTLCache O(N) Eviction Blocking
**Learning:** In a `TTLCache`, periodically evicting expired items via an O(N) scan during `get()` calls can severely degrade performance to O(N) when the cache utilization is high (e.g., >90%). This blocks otherwise O(1) read operations and causes significant lag.
**Action:** Always implement a timestamp-based throttling mechanism (e.g., `_last_evict_time`) to limit the frequency of background O(N) scans inside high-frequency read paths.
