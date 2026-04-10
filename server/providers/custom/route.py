from server.providers.common.request_builder import auth_headers
from server.providers.common.result_builder import error_result, success_result
from server.utils.json_utils import safe_json_dumps


async def route(http_client, auth, config, origin, destination):
    route_url = config.get("routeUrl")
    if not route_url:
        return error_result("config_error", "routeUrl", "缺少导航接口地址")
    status, data = await http_client.post_json(
        route_url,
        json_body={
            "origin": origin,
            "destination": destination,
            "language": "zh",
            "coordType": "wgs84",
            "countryArea": "china",
        },
        headers=auth_headers(auth),
    )
    if status != 200:
        return error_result("network_error", route_url, safe_json_dumps(data))
    distance_value = (data.get("distance") or {}).get("value")
    duration_value = (data.get("duration") or {}).get("value")
    if distance_value is None or duration_value is None:
        return error_result("no_result", route_url, safe_json_dumps(data))
    return success_result(distanceKm=round(distance_value / 1000, 2), durationMin=round(duration_value / 60))
