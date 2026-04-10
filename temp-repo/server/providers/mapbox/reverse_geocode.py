from server.providers.common.result_builder import error_result, success_result
from server.utils.coords import round_coord
from server.utils.json_utils import safe_json_dumps


async def reverse_geocode(http_client, auth, _config, lat, lng):
    norm_lat = round_coord(lat)
    norm_lng = round_coord(lng)
    url = (
        "https://api.mapbox.com/geocoding/v5/mapbox.places/"
        f"{norm_lng},{norm_lat}.json?access_token={auth}"
    )
    status, data = await http_client.get_json(url)
    if status != 200:
        return error_result("network_error", url, safe_json_dumps(data))
    features = data.get("features") or []
    if not features:
        return error_result("no_result", url, safe_json_dumps(data))
    return success_result(address=features[0].get("place_name", ""), lat=norm_lat, lng=norm_lng)
