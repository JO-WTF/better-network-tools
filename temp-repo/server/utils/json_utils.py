import json


def safe_json_dumps(data):
    return json.dumps(data, ensure_ascii=False)
