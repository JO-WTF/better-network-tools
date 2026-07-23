from server.providers.common.request_builder import auth_headers
from server.providers.common.result_builder import error_result, success_result
from server.utils.coords import round_coord
from server.utils.json_utils import safe_json_dumps


async def reverse_geocode(http_client, auth, config, lat, lng):
    reverse_geocode_url = config.get("reverseGeocodeUrl") or config.get("reverse_geocode_url")
    if not reverse_geocode_url:
        return error_result(
            "config_error",
            "reverseGeocodeUrl",
            "缺少反向地理编码接口地址",
        )

    payload = {
        "location": {
            "lat": round_coord(lat),
            "lng": round_coord(lng),
        },
        "coordType": "wgs84",
    }

    status, data = await http_client.post_json(
        reverse_geocode_url,
        json_body=payload,
        headers=auth_headers(auth),
    )

    if status != 200 or not isinstance(data, dict):
        return error_result("network_error", reverse_geocode_url, safe_json_dumps(data))

    result = data.get("result") or {}
    result_address = result.get("address") if isinstance(result, dict) else None
    address = result_address or data.get("address") or data.get("label")
    if not address:
        address = safe_json_dumps(data)
        return error_result("no_result", reverse_geocode_url, address)

    return success_result(address=address, lat=round_coord(lat), lng=round_coord(lng))
