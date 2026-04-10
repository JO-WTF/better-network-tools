class GeocodeService:
    def __init__(self, provider_registry, auth_service, cache_manager):
        self.provider_registry = provider_registry
        self.auth_service = auth_service
        self.cache_manager = cache_manager

    async def execute(self, http_client, config, address, conn_cache):
        provider_name = self.provider_registry.detect_provider(config)
        provider = self.provider_registry.get(provider_name)
        if address in conn_cache:
            return conn_cache[address]
        persistent = self.cache_manager.get_persistent_cache(
            "geocode", provider_name, config.get("geocodeUrl") or "default"
        )
        cached = persistent.get(address)
        if cached is not None:
            conn_cache[address] = cached
            return cached
        auth = await self.auth_service.get_auth(provider, http_client, config)
        if provider_name == "custom" and not auth:
            return {
                "success": False,
                "errorType": "auth_error",
                "request": config.get("tokenUrl", "token"),
                "response": "无法获取 Token",
            }
        result = await provider.geocode(http_client, auth, config, address)
        conn_cache[address] = result
        persistent.set(address, result)
        return result
