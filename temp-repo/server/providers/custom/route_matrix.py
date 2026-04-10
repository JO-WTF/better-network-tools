from server.providers.common.request_builder import auth_headers
from server.providers.common.result_builder import error_result
from server.utils.json_utils import safe_json_dumps


def _normalize_coord(value: str):
    raw = str(value or "").strip()
    if not raw:
        return None
    delimiter = "," if "," in raw else "，" if "，" in raw else None
    if not delimiter:
        return None
    parts = [item.strip() for item in raw.split(delimiter)]
    if len(parts) < 2:
        return None
    try:
        lng = round(float(parts[0]), 6)
        lat = round(float(parts[1]), 6)
    except ValueError:
        return None
    return lat, lng


def _fmt_latlng(lat: float, lng: float) -> str:
    return f"{float(lat):.6f},{float(lng):.6f}"


def _parse_matrix_response(data, origins, destinations):
    parsed = {}
    if isinstance(data, str):
        return parsed
    if not isinstance(data, dict):
        return parsed

    status = data.get("status")
    if status in (400, "400", "NG"):
        return parsed
    if status not in {"OK", "SUCCESS", 0, "0", None} and "results" not in data:
        return parsed

    ori_lookup = {_fmt_latlng(item["lat"], item["lng"]): item["id"] for item in origins}
    dst_lookup = {_fmt_latlng(item["lat"], item["lng"]): item["id"] for item in destinations}

    for item in data.get("results") or []:
        origin = item.get("origin", "")
        destination = item.get("destination", "")
        origin_id = ori_lookup.get(origin)
        destination_id = dst_lookup.get(destination)

        if origin_id is None or destination_id is None:
            normalized_origin = _normalize_coord(origin)
            normalized_destination = _normalize_coord(destination)
            if normalized_origin:
                origin_id = ori_lookup.get(_fmt_latlng(normalized_origin[0], normalized_origin[1]))
            if normalized_destination:
                destination_id = dst_lookup.get(_fmt_latlng(normalized_destination[0], normalized_destination[1]))

        if origin_id is None or destination_id is None:
            continue

        distance = item.get("distance")
        duration = item.get("duration")
        if distance is None or duration is None:
            continue

        parsed[(origin_id, destination_id)] = {
            "distanceKm": round(float(distance) / 1000.0, 2),
            "durationMin": round(float(duration) / 60.0),
        }

    return parsed


async def route_matrix(http_client, auth, config, routes):
    route_url = config.get("routeUrl")
    if not route_url:
        return error_result("config_error", "routeUrl", "缺少导航接口地址")

    point_lookup = {}
    route_pairs = []
    for item in routes:
        origin = _normalize_coord(item.get("origin"))
        destination = _normalize_coord(item.get("destination"))
        if not origin or not destination:
            continue
        point_lookup.setdefault(_fmt_latlng(*origin), origin)
        point_lookup.setdefault(_fmt_latlng(*destination), destination)
        route_pairs.append((item.get("index"), origin, destination))

    if not route_pairs:
        return {
            "success": True,
            "results": [],
        }

    points = list(point_lookup.values())
    origins = [{"id": idx, "lat": lat, "lng": lng} for idx, (lat, lng) in enumerate(points)]
    destinations = origins

    sep = "%7C"
    payload = {
        "origin": sep.join(_fmt_latlng(p["lat"], p["lng"]) for p in origins),
        "destination": sep.join(_fmt_latlng(p["lat"], p["lng"]) for p in destinations),
        "matrix": "true",
        "language": "en",
        "coordType": "wgs84",
    }

    status, data = await http_client.post_json(
        route_url,
        json_body=payload,
        headers=auth_headers(auth),
    )
    if status != 200:
        return error_result("network_error", route_url, safe_json_dumps(data))

    parsed = _parse_matrix_response(data, origins, destinations)
    coord_to_id = {_fmt_latlng(p["lat"], p["lng"]): p["id"] for p in origins}

    results = []
    for row_index, origin, destination in route_pairs:
        origin_id = coord_to_id.get(_fmt_latlng(*origin))
        destination_id = coord_to_id.get(_fmt_latlng(*destination))
        item = parsed.get((origin_id, destination_id)) if origin_id is not None and destination_id is not None else None
        if item:
            results.append({
                "index": row_index,
                "success": True,
                "distanceKm": item["distanceKm"],
                "durationMin": item["durationMin"],
                "originLat": origin[0],
                "originLng": origin[1],
                "destinationLat": destination[0],
                "destinationLng": destination[1],
            })
        else:
            results.append({
                "index": row_index,
                "success": False,
                "errorType": "no_result",
                "request": route_url,
                "response": safe_json_dumps(data),
                "originLat": origin[0],
                "originLng": origin[1],
                "destinationLat": destination[0],
                "destinationLng": destination[1],
            })

    return {
        "success": True,
        "results": results,
    }
