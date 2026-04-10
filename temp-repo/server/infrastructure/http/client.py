import aiohttp


class HttpClient:
    def __init__(self, timeout_s: int = 30):
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_s))

    async def post_json(self, url: str, *, json_body: dict, headers: dict | None = None):
        async with self._session.post(url, json=json_body, headers=headers or {}, ssl=False) as response:
            data = await response.json()
            return response.status, data

    async def get_json(self, url: str, *, headers: dict | None = None):
        async with self._session.get(url, headers=headers or {}, ssl=False) as response:
            data = await response.json()
            return response.status, data

    async def close(self):
        await self._session.close()
