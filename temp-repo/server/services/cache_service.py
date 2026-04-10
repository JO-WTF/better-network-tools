from server.infrastructure.cache.memory_cache import MemoryCache


class CacheService:
    def __init__(self):
        self.geocode_cache = MemoryCache()
        self.route_cache = MemoryCache()
