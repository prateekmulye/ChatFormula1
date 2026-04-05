import time
from src.utils.cache import TTLCache
import logging

logging.getLogger('src.utils.cache').setLevel(logging.WARNING)

# Setup cache near capacity
cache = TTLCache(max_size=10000, default_ttl=300)
for i in range(9500):
    cache.set(f"key{i}", i)

# Now we mock the len check to avoid O(N) cleanup on get
# The issue is self._evict_expired() is O(N) in `TTLCache.get`

class FastTTLCache(TTLCache):
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        super().__init__(max_size, default_ttl)
        self._last_evict_time = 0.0

    def get(self, key: str):
        # Throttle eviction to at most once per second
        current_time = time.time()
        if len(self._cache) > self.max_size * 0.9 and current_time - self._last_evict_time > 1.0:
            self._evict_expired()
            self._last_evict_time = current_time

        if key in self._cache:
            value, expiry = self._cache[key]
            if self._is_expired(expiry):
                del self._cache[key]
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return value

        self._misses += 1
        return None

cache2 = FastTTLCache(max_size=10000, default_ttl=300)
for i in range(9500):
    cache2.set(f"key{i}", i)

start = time.time()
for i in range(1000):
    cache2.get(f"key{i}")
end = time.time()
print(f"Time taken after patch: {end - start:.5f}s")
