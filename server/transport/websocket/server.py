import websockets


async def run_websocket_server(handler, host: str, port: int, max_size: int):
    async with websockets.serve(handler, host, port, max_size=max_size):
        await __import__("asyncio").Future()
