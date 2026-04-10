from server.config.settings import get_settings
from server.infrastructure.cache.cache_manager import CacheManager
from server.infrastructure.http.client import HttpClient
from server.services.auth_service import AuthService
from server.services.geocode_service import GeocodeService
from server.services.provider_registry import ProviderRegistry
from server.services.route_service import RouteService
from server.services.route_matrix_service import RouteMatrixService
from server.transport.websocket.handler import WebSocketHandler


def build_dependencies():
    settings = get_settings()
    provider_registry = ProviderRegistry()
    auth_service = AuthService()
    cache_manager = CacheManager(settings.cache_dir)
    geocode_service = GeocodeService(provider_registry, auth_service, cache_manager)
    route_service = RouteService(provider_registry, auth_service, cache_manager)
    route_matrix_service = RouteMatrixService(provider_registry, auth_service, cache_manager)
    ws_handler = WebSocketHandler(
        geocode_service,
        route_service,
        route_matrix_service,
        lambda: HttpClient(settings.request_timeout_s),
    )
    return settings, ws_handler
