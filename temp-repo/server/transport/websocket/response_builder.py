import json


def progress(payload):
    return json.dumps({"type": "progress", "payload": payload}, ensure_ascii=False)


def complete():
    return json.dumps({"type": "complete"}, ensure_ascii=False)
