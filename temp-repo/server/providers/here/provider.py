from server.providers.base.provider import Provider
from server.providers.here.geocode import geocode
from server.providers.here.reverse_geocode import reverse_geocode
from server.providers.here.route import route
from server.providers.here.token import fetch_token


class HereProvider(Provider):
    name = "here"

    async def get_auth(self, http_client, config):
        return await fetch_token(http_client, config)

    async def geocode(self, http_client, auth, config, address):
        return await geocode(http_client, auth, config, address)

    async def reverse_geocode(self, http_client, auth, config, lat, lng):
        return await reverse_geocode(http_client, auth, config, lat, lng)

    async def route(self, http_client, auth, config, origin, destination):
        return await route(http_client, auth, config, origin, destination)
