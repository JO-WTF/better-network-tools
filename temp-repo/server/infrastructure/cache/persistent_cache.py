import json
from pathlib import Path


class PersistentCache:
    def __init__(self, cache_file: Path, flush_batch: int):
        self.path = cache_file
        self.flush_batch = flush_batch
        self.store = self._load()
        self.pending = 0

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value
        self.pending += 1
        if self.pending >= self.flush_batch:
            self.flush()

    def flush(self):
        if self.pending <= 0:
            return
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.store, f, ensure_ascii=False)
        self.pending = 0
