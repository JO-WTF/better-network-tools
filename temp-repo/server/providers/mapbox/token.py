async def fetch_token(_http_client, config):
    return config.get("apiKey", "")
