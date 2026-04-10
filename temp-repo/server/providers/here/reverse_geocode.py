from server.providers.common.result_builder import error_result, success_result
from server.utils.coords import round_coord
from server.utils.json_utils import safe_json_dumps


async def reverse_geocode(http_client, auth, _config, lat, lng):
    norm_lat = round_coord(lat)
    norm_lng = round_coord(lng)
    url = f"https://revgeocode.search.hereapi.com/v1/revgeocode?at={norm_lat},{norm_lng}&lang=zh-CN&apiKey={auth}"
    status, data = await http_client.get_json(url)
    if status != 200:
        return error_result("network_error", url, safe_json_dumps(data))
    items = data.get("items") or []
    if not items:
        return error_result("no_result", url, safe_json_dumps(data))
    address = (items[0].get("address") or {}).get("label") or ""
    return success_result(address=address, lat=norm_lat, lng=norm_lng)
