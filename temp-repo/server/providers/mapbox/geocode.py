from urllib.parse import quote

from server.providers.common.result_builder import error_result, success_result
from server.utils.coords import round_coord
from server.utils.json_utils import safe_json_dumps


async def geocode(http_client, auth, _config, address):
    query = quote(str(address or "").strip())
    if not query:
        return error_result("invalid", "address", "地址为空")
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json?access_token={auth}"
    status, data = await http_client.get_json(url)
    if status != 200:
        return error_result("network_error", url, safe_json_dumps(data))
    features = data.get("features") or []
    if not features:
        return error_result("no_result", url, safe_json_dumps(data))
    center = features[0].get("center") or []
    if len(center) < 2:
        return error_result("no_result", url, safe_json_dumps(data))
    lng, lat = center[0], center[1]
    return success_result(lat=round_coord(lat), lng=round_coord(lng))
