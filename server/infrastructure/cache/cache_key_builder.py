def build_cache_key(*parts):
    return "|".join(str(p) for p in parts)
