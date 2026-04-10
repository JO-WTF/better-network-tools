class Provider:
    name = "base"

    async def get_auth(self, http_client, config):
        return ""

    async def geocode(self, http_client, auth, config, address):
        raise NotImplementedError

    async def route(self, http_client, auth, config, origin, destination):
        raise NotImplementedError

    async def route_matrix(self, http_client, auth, config, routes):
        raise NotImplementedError
