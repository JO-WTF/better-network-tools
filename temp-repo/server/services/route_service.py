class RouteService:
    def __init__(self, provider_registry, auth_service, cache_manager):
        self.provider_registry = provider_registry
        self.auth_service = auth_service
        self.cache_manager = cache_manager

    async def execute(self, http_client, config, origin, destination, conn_cache):
        provider_name = self.provider_registry.detect_provider(config)
        provider = self.provider_registry.get(provider_name)
        key = (origin, destination)
        if key in conn_cache:
            return conn_cache[key]
        persistent = self.cache_manager.get_persistent_cache(
            "route", provider_name, config.get("routeUrl") or "default"
        )
        persistent_key = f"{origin}|{destination}"
        cached = persistent.get(persistent_key)
        if cached is not None:
            conn_cache[key] = cached
            return cached
        auth = await self.auth_service.get_auth(provider, http_client, config)
        if provider_name == "custom" and not auth:
            return {
                "success": False,
                "errorType": "auth_error",
                "request": config.get("tokenUrl", "token"),
                "response": "无法获取 Token",
            }
        result = await provider.route(http_client, auth, config, origin, destination)
        conn_cache[key] = result
        persistent.set(persistent_key, result)
        return result
