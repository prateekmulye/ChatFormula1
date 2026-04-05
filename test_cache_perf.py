import time
from src.utils.cache import TTLCache
import logging

# Setup cache near capacity
cache = TTLCache(max_size=10000, default_ttl=300)
for i in range(9500):
    cache.set(f"key{i}", i)

# Measure get time
start = time.time()
for i in range(100):
    cache.get(f"key{i}")
end = time.time()
print(f"Time taken: {end - start:.5f}s")
