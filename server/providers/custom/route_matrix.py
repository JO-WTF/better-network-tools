from collections import defaultdict

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
        first = round(float(parts[0]), 6)
        second = round(float(parts[1]), 6)
    except ValueError:
        return None

    # 优先按 lat,lng 解析（与 server 内部坐标字符串保持一致）
    if -90 <= first <= 90 and -180 <= second <= 180:
        return first, second

    # 兼容历史 lng,lat 输入
    if -180 <= first <= 180 and -90 <= second <= 90:
        return second, first

    return None


def _fmt_latlng(lat: float, lng: float) -> str:
    return f"{float(lat):.6f},{float(lng):.6f}"


def _parse_matrix_response(data, origins, destinations):
    parsed = {}
    if isinstance(data, str) or not isinstance(data, dict):
        return parsed

    ori_lookup = {_fmt_latlng(item["lat"], item["lng"]): item["id"] for item in origins}
    dst_lookup = {_fmt_latlng(item["lat"], item["lng"]): item["id"] for item in destinations}

    payload_data = data.get("data")
    matrix_results = payload_data.get("matrixResults") if isinstance(payload_data, dict) else None
    result_items = matrix_results or data.get("results") or []
    for item in result_items:
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


async def _call_matrix_batch(http_client, route_url, headers, origins, destinations):
    payload = {
        "origin": "|".join(_fmt_latlng(p["lat"], p["lng"]) for p in origins),
        "destination": "|".join(_fmt_latlng(p["lat"], p["lng"]) for p in destinations),
        "matrix": "true",
        "language": "en",
        "coordType": "wgs84",
    }

    status, data = await http_client.post_json(
        route_url,
        json_body=payload,
        headers=headers,
    )
    if status != 200:
        return status, data, {}

    return status, data, _parse_matrix_response(data, origins, destinations)


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
        return {"success": True, "results": []}

    points = list(point_lookup.values())
    point_id_lookup = {_fmt_latlng(lat, lng): idx for idx, (lat, lng) in enumerate(points)}
    points_with_id = [{"id": idx, "lat": lat, "lng": lng} for idx, (lat, lng) in enumerate(points)]

    missing_pairs = set()
    grouped_destinations = defaultdict(set)
    for _, origin, destination in route_pairs:
        origin_key = _fmt_latlng(*origin)
        destination_key = _fmt_latlng(*destination)
        origin_id = point_id_lookup.get(origin_key)
        destination_id = point_id_lookup.get(destination_key)
        if origin_id is None or destination_id is None:
            continue
        missing_pairs.add((origin_id, destination_id))
        grouped_destinations[origin_id].add(destination_id)

    headers = auth_headers(auth)
    parsed = {}
    last_error = None

    for origin_id, destination_ids in grouped_destinations.items():
        destination_ids = list(destination_ids)
        origin_point = [points_with_id[origin_id]]
        for i in range(0, len(destination_ids), 10):
            batch_destination_ids = destination_ids[i : i + 10]
            destination_points = [points_with_id[d_id] for d_id in batch_destination_ids]

            status, data, batch_parsed = await _call_matrix_batch(
                http_client,
                route_url,
                headers,
                origin_point,
                destination_points,
            )

            if status == 401:
                refreshed_auth = config.get("token")
                if not refreshed_auth:
                    from server.providers.custom.token import fetch_token

                    refreshed_auth = await fetch_token(http_client, config)
                if refreshed_auth:
                    headers = auth_headers(refreshed_auth)
                    status, data, batch_parsed = await _call_matrix_batch(
                        http_client,
                        route_url,
                        headers,
                        origin_point,
                        destination_points,
                    )

            if status != 200:
                last_error = (status, data)
                continue

            parsed.update(batch_parsed)

    results = []
    for row_index, origin, destination in route_pairs:
        origin_id = point_id_lookup.get(_fmt_latlng(*origin))
        destination_id = point_id_lookup.get(_fmt_latlng(*destination))
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
            missing_pairs.discard((origin_id, destination_id))
            results.append({
                "index": row_index,
                "success": False,
                "errorType": "no_result",
                "request": route_url,
                "response": safe_json_dumps(last_error[1]) if last_error else "无可用路径结果",
                "originLat": origin[0],
                "originLng": origin[1],
                "destinationLat": destination[0],
                "destinationLng": destination[1],
            })

    return {
        "success": True,
        "results": results,
    }
