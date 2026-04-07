import time
from src.utils.cache import TTLCache

cache = TTLCache(max_size=10000, default_ttl=300)

# fill cache to 95%
for i in range(9500):
    cache.set(f"key{i}", i)

start = time.time()
for i in range(100):
    cache.get(f"key{i}")
end = time.time()

print(f"Time taken for 100 gets: {end - start} seconds")
