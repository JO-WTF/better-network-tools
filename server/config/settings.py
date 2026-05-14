from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from server.config.custom_config import CustomProviderConfig


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8765
    request_timeout_s: int = 30
    max_connections: int = 100
    cache_dir: Path = Path(__file__).resolve().parents[2] / "cache"
    custom: CustomProviderConfig = CustomProviderConfig()


def _load_custom_from_ini(config_path: Path) -> CustomProviderConfig:
    parser = ConfigParser()
    parser.read(config_path, encoding="utf-8")
    section = parser["custom"] if parser.has_section("custom") else {}
    return CustomProviderConfig(
        app_id=section.get("app_id", ""),
        credential=section.get("credential", ""),
        token_url=section.get("token_url", "getResAppDynamicToken"),
        geocode_url=section.get("geocode_url", "geographicSearch"),
        route_url=section.get("route_url", "routeSearch"),
    )


def get_settings() -> Settings:
    settings = Settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    config_path = Path(__file__).resolve().parents[2] / "config.ini"
    if config_path.exists():
        settings.custom = _load_custom_from_ini(config_path)
    return settings
