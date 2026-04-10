from pathlib import Path

from server.config.constants import CACHE_FLUSH_BATCH
from server.infrastructure.cache.persistent_cache import PersistentCache
from server.utils.hash_utils import short_md5


class CacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self._caches = {}

    def get_persistent_cache(self, capability: str, provider: str, endpoint: str):
        key = f"{capability}_{provider}_{endpoint}"
        if key not in self._caches:
            digest = short_md5(endpoint or "default")
            cache_file = self.cache_dir / f"{capability}_{provider}_{digest}.json"
            self._caches[key] = PersistentCache(cache_file, CACHE_FLUSH_BATCH)
        return self._caches[key]
