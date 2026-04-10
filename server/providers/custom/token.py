from server.providers.common.response_parser import nested_get


async def fetch_token(http_client, config):
    token_url = config.get("tokenUrl")
    if not token_url:
        return ""
    status, data = await http_client.post_json(
        token_url,
        json_body={
            "appId": config.get("appId", ""),
            "credential": config.get("credential", ""),
        },
    )
    if status != 200:
        return ""
    if nested_get(data, "status", "statusCode") != "SUCCESS":
        return ""
    return data.get("result", "")
