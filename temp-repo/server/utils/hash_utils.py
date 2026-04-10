import hashlib


def short_md5(text: str, length: int = 12) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:length]
