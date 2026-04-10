import json


def parse_ws_message(message: str):
    payload = json.loads(message)
    if payload.get("type") != "start":
        return None
    return payload.get("payload", {})
