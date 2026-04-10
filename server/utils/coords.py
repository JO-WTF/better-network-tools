from server.config.constants import COORD_PRECISION


def round_coord(value):
    if value is None:
        return None
    return round(float(value), COORD_PRECISION)


def format_coord_pair(lat, lng):
    return f"{round_coord(lat):.{COORD_PRECISION}f},{round_coord(lng):.{COORD_PRECISION}f}"


def parse_coordinate(value):
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
        lng = round_coord(parts[0])
        lat = round_coord(parts[1])
    except ValueError:
        return None
    return lat, lng
