from server.providers.common.result_builder import error_result, success_result
from server.utils.coords import round_coord
from server.utils.json_utils import safe_json_dumps


def _parse_lat_lng(pair: str):
    parts = [p.strip() for p in str(pair or "").split(",")]
    if len(parts) < 2:
        return None
    try:
        lat = round_coord(parts[0])
        lng = round_coord(parts[1])
    except ValueError:
        return None
    return lat, lng


async def route(http_client, auth, _config, origin, destination):
    origin_pair = _parse_lat_lng(origin)
    destination_pair = _parse_lat_lng(destination)
    if not origin_pair or not destination_pair:
        return error_result("invalid", "coordinate", "坐标格式错误")
    o_lat, o_lng = origin_pair
    d_lat, d_lng = destination_pair
    url = (
        "https://api.mapbox.com/directions/v5/mapbox/driving/"
        f"{o_lng},{o_lat};{d_lng},{d_lat}?geometries=geojson&overview=full&access_token={auth}"
    )
    status, data = await http_client.get_json(url)
    if status != 200:
        return error_result("network_error", url, safe_json_dumps(data))
    routes = data.get("routes") or []
    if not routes:
        return error_result("no_result", url, safe_json_dumps(data))
    first = routes[0]
    distance = first.get("distance")
    duration = first.get("duration")
    if distance is None or duration is None:
        return error_result("no_result", url, safe_json_dumps(data))
    return success_result(distanceKm=round(distance / 1000, 2), durationMin=round(duration / 60))
