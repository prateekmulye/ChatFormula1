## 2026-03-24 - Throttling Cache Eviction on Read Path
**Learning:** O(N) cache eviction scans on read paths (like `.get()`) can destroy O(1) performance guarantees and cause severe bottlenecks under heavy load, especially as cache sizes grow.
**Action:** Throttle eviction scans on read paths using a timestamp mechanism (e.g., minimum 60-second interval between scans) to maintain consistent O(1) read latency.
