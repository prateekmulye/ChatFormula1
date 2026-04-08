## 2024-05-15 - TTLCache O(N) Eviction Blocking
**Learning:** Calling an O(N) background eviction scan (`_evict_expired()`) directly within an O(1) read path (`get()`) based only on a static size threshold (e.g., `> 90%` capacity) causes massive performance degradation under high load. Every `get` triggers an O(N) scan.
**Action:** Always implement a timestamp-based throttling mechanism (e.g., `_last_evict_time`) to limit the frequency of O(N) maintenance operations inside hot read paths.
