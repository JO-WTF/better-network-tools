import asyncio

from server.config.constants import WS_MAX_SIZE
from server.dependency import build_dependencies
from server.transport.http_api import run_http_api
from server.transport.websocket.server import run_websocket_server


async def main():
    settings, ws_handler = build_dependencies()
    await asyncio.gather(
        run_websocket_server(
            ws_handler.handle_connection,
            settings.host,
            settings.port,
            WS_MAX_SIZE,
        ),
        run_http_api(
            settings.host,
            settings.http_port,
            settings.scheme_dir,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
