import asyncio

from server.config.constants import WS_MAX_SIZE
from server.dependency import build_dependencies
from server.transport.websocket.server import run_websocket_server


async def main():
    settings, ws_handler = build_dependencies()
    await run_websocket_server(
        ws_handler.handle_connection,
        settings.host,
        settings.port,
        WS_MAX_SIZE,
    )


if __name__ == "__main__":
    asyncio.run(main())
