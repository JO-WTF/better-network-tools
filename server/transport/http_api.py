import asyncio
import json
from pathlib import Path

from aiohttp import web


def _safe_share_id(value: str) -> str:
    cleaned = "".join(ch for ch in (value or "") if ch.isalnum() or ch in ("-", "_"))
    if not cleaned:
        raise web.HTTPBadRequest(text="invalid share id")
    return cleaned


def _scheme_file(scheme_dir: Path, share_id: str) -> Path:
    return scheme_dir / f"{_safe_share_id(share_id)}.json"


async def get_scheme(request: web.Request) -> web.Response:
    scheme_dir: Path = request.app["scheme_dir"]
    share_id = request.match_info.get("share_id", "")
    path = _scheme_file(scheme_dir, share_id)
    if not path.exists():
        raise web.HTTPNotFound(text="scheme not found")
    return web.json_response(json.loads(path.read_text(encoding="utf-8")))


async def put_scheme(request: web.Request) -> web.Response:
    scheme_dir: Path = request.app["scheme_dir"]
    share_id = request.match_info.get("share_id", "")
    payload = await request.json()
    payload["shareId"] = _safe_share_id(share_id)
    path = _scheme_file(scheme_dir, share_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return web.json_response({"ok": True, "shareId": payload["shareId"]})


async def run_http_api(host: str, port: int, scheme_dir: Path):
    app = web.Application()
    app["scheme_dir"] = scheme_dir
    app.router.add_get("/api/schemes/{share_id}", get_scheme)
    app.router.add_put("/api/schemes/{share_id}", put_scheme)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()
