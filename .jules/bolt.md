## 2026-04-16 - Prevent O(N) cache background eviction scans from blocking O(1) read paths
**Learning:** The TTLCache in `src/utils/cache.py` utilizes a timestamp-based throttling mechanism (`self._last_evict_time`) to prevent O(N) background eviction scans from blocking O(1) read paths (`get()`) during high cache utilization. Oh wait, it doesn't currently do this. I'll add this optimization.
**Action:** When implementing cache eviction, use a throttle mechanism to prevent excessive O(N) scans on every cache hit.
