from urllib.parse import quote

from server.providers.common.result_builder import error_result, success_result
from server.utils.coords import round_coord
from server.utils.json_utils import safe_json_dumps


async def geocode(http_client, auth, _config, address):
    query = quote(str(address or "").strip())
    if not query:
        return error_result("invalid", "address", "地址为空")
    url = f"https://geocode.search.hereapi.com/v1/geocode?q={query}&apiKey={auth}"
    status, data = await http_client.get_json(url)
    if status != 200:
        return error_result("network_error", url, safe_json_dumps(data))
    items = data.get("items") or []
    if not items:
        return error_result("no_result", url, safe_json_dumps(data))
    pos = items[0].get("position") or {}
    lat = pos.get("lat")
    lng = pos.get("lng")
    if lat is None or lng is None:
        return error_result("no_result", url, safe_json_dumps(data))
    return success_result(lat=round_coord(lat), lng=round_coord(lng))
