def auth_headers(token: str | None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    return headers
