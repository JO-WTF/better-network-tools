from dataclasses import dataclass


@dataclass(frozen=True)
class CustomProviderConfig:
    app_id: str = ""
    credential: str = ""
    token_url: str = "getResAppDynamicToken"
    geocode_url: str = "geographicSearch"
    route_url: str = "routeSearch"
