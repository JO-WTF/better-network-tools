class AuthService:
    async def get_auth(self, provider, http_client, config):
        return await provider.get_auth(http_client, config)
