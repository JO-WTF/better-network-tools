from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8765
    request_timeout_s: int = 30
    max_connections: int = 100
    cache_dir: Path = Path(__file__).resolve().parents[2] / "cache"


def get_settings() -> Settings:
    settings = Settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
