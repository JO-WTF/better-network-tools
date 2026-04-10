from server.providers.custom.provider import CustomProvider
from server.providers.here.provider import HereProvider
from server.providers.mapbox.provider import MapboxProvider


class ProviderRegistry:
    def __init__(self):
        self.providers = {
            "custom": CustomProvider(),
            "mapbox": MapboxProvider(),
            "here": HereProvider(),
        }

    def detect_provider(self, config: dict) -> str:
        explicit_provider = str(config.get("provider") or "").lower().strip()
        if explicit_provider in self.providers:
            return explicit_provider

        geocode_url = str(config.get("geocodeUrl") or "").lower()
        route_url = str(config.get("routeUrl") or "").lower()
        combined = f"{geocode_url} {route_url}"
        if "mapbox" in combined:
            return "mapbox"
        if "here" in combined:
            return "here"
        if geocode_url or route_url or config.get("tokenUrl"):
            return "custom"
        return "custom"

    def get(self, provider_name: str):
        return self.providers.get(provider_name, self.providers["custom"])
