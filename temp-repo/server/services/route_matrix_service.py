class RouteMatrixService:
    def __init__(self, provider_registry, auth_service, cache_manager):
        self.provider_registry = provider_registry
        self.auth_service = auth_service
        self.cache_manager = cache_manager

    async def execute(self, http_client, config, routes):
        provider_name = self.provider_registry.detect_provider(config)
        provider = self.provider_registry.get(provider_name)
        auth = await self.auth_service.get_auth(provider, http_client, config)
        if provider_name == "custom" and not auth:
            return {
                "success": False,
                "errorType": "auth_error",
                "request": config.get("tokenUrl", "token"),
                "response": "无法获取 Token",
            }
        return await provider.route_matrix(http_client, auth, config, routes)
