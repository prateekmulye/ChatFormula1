import time
from src.utils.cache import TTLCache
import logging

logging.getLogger('src.utils.cache').setLevel(logging.WARNING)

# Setup cache near capacity
cache = TTLCache(max_size=10000, default_ttl=300)
for i in range(9500):
    cache.set(f"key{i}", i)

start = time.time()
for i in range(1000):
    cache.get(f"key{i}")
end = time.time()
print(f"Time taken before patch: {end - start:.5f}s")
