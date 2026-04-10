class BaseService:
    def __init__(self, provider_registry, auth_service, cache_manager):
        self.provider_registry = provider_registry
        self.auth_service = auth_service
        self.cache_manager = cache_manager
