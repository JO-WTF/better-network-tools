from server.providers.common.request_builder import auth_headers
from server.providers.common.response_parser import nested_get
from server.providers.common.result_builder import error_result, success_result
from server.utils.coords import round_coord
from server.utils.json_utils import safe_json_dumps


async def geocode(http_client, auth, config, address):
    geocode_url = config.get("geocodeUrl")
    if not geocode_url:
        return error_result("config_error", "geocodeUrl", "缺少地理编码接口地址")
    status, data = await http_client.post_json(
        geocode_url,
        json_body={"address": str(address or "").strip(), "language": "en", "coordType": "wgs84"},
        headers=auth_headers(auth),
    )
    if status != 200 or data.get("status") != "OK":
        return error_result("network_error", geocode_url, safe_json_dumps(data))
    lat = nested_get(data, "result", "geometry", "location", "lat")
    lng = nested_get(data, "result", "geometry", "location", "lng")
    if lat is None or lng is None:
        return error_result("no_result", geocode_url, safe_json_dumps(data))
    return success_result(lat=round_coord(lat), lng=round_coord(lng))
