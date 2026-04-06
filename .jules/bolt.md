## 2025-02-24 - Throttling Cache Eviction Scans
**Learning:** Background cache eviction scans that are an O(N) operation triggered during the O(1) read path (like a `get()` call) can severely bottleneck performance under high cache utilization when not throttled.
**Action:** Implement a timestamp-based throttling mechanism (e.g., executing the scan at most once per second) to prevent read latency spikes while maintaining reasonable cache efficiency.
