from server.providers.base.provider import Provider
from server.providers.custom.geocode import geocode
from server.providers.custom.reverse_geocode import reverse_geocode
from server.providers.custom.route import route
from server.providers.custom.route_matrix import route_matrix
from server.providers.custom.token import fetch_token


class CustomProvider(Provider):
    name = "custom"

    async def get_auth(self, http_client, config):
        return await fetch_token(http_client, config)

    async def geocode(self, http_client, auth, config, address):
        return await geocode(http_client, auth, config, address)

    async def reverse_geocode(self, http_client, auth, config, lat, lng):
        return await reverse_geocode(http_client, auth, config, lat, lng)

    async def route(self, http_client, auth, config, origin, destination):
        return await route(http_client, auth, config, origin, destination)

    async def route_matrix(self, http_client, auth, config, routes, progress_callback=None):
        return await route_matrix(http_client, auth, config, routes, progress_callback=progress_callback)
