class RouteCapability:
    async def route(self, http_client, auth, config, origin, destination):
        raise NotImplementedError
