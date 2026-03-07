## 2024-05-14 - Throttle cache eviction
**Learning:** TTLCache in src/utils/cache.py uses O(N) sweep across all entries on get() when cache size is near max capacity, causing severe latency spikes.
**Action:** Throttle eviction sweeps with a timestamp so they run at most once per minute.
