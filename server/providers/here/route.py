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
        "https://router.hereapi.com/v8/routes?transportMode=car"
        f"&origin={o_lat},{o_lng}&destination={d_lat},{d_lng}&return=summary,polyline&apiKey={auth}"
    )
    status, data = await http_client.get_json(url)
    if status != 200:
        return error_result("network_error", url, safe_json_dumps(data))
    routes = data.get("routes") or []
    if not routes:
        return error_result("no_result", url, safe_json_dumps(data))
    sections = routes[0].get("sections") or []
    if not sections:
        return error_result("no_result", url, safe_json_dumps(data))
    summary = sections[0].get("summary") or {}
    distance = summary.get("length")
    duration = summary.get("duration")
    if distance is None or duration is None:
        return error_result("no_result", url, safe_json_dumps(data))
    return success_result(distanceKm=round(distance / 1000, 2), durationMin=round(duration / 60))
