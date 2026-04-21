## 2024-04-21 - Optimized TTLCache eviction throttling
**Learning:** Found a major bottleneck in src/utils/cache.py where the TTLCache had an O(N) background eviction scan blocking O(1) read paths (get()) during high cache utilization. Utilizing a timestamp-based throttling mechanism via _last_evict_time significantly reduces latency spikes under load.
**Action:** When implementing caching mechanisms, throttle cache evictions over a duration rather than per get().
