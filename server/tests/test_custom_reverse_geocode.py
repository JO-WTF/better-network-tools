import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from server.config.settings import _load_custom_from_ini
from server.providers.custom.provider import CustomProvider
from server.providers.custom.reverse_geocode import reverse_geocode
from server.transport.websocket.handler import WebSocketHandler


class FakeHttpClient:
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = data
        self.requests = []

    async def post_json(self, url, *, json_body, headers=None):
        self.requests.append((url, json_body, headers))
        return self.status, self.data


class CustomReverseGeocodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_url(self):
        result = await reverse_geocode(FakeHttpClient(), "token", {}, 39.9, 116.4)

        self.assertFalse(result["success"])
        self.assertEqual(result["errorType"], "config_error")

    async def test_posts_location_and_returns_address(self):
        http_client = FakeHttpClient(data={"result": {"address": "北京市朝阳区"}})

        result = await reverse_geocode(
            http_client,
            "token",
            {"reverseGeocodeUrl": "https://geo.example/reverse"},
            39.9000004,
            116.4000004,
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "address": "北京市朝阳区",
                "lat": 39.9,
                "lng": 116.4,
            },
        )
        url, payload, headers = http_client.requests[0]
        self.assertEqual(url, "https://geo.example/reverse")
        self.assertEqual(payload["location"], {"lat": 39.9, "lng": 116.4})
        self.assertEqual(headers["Authorization"], "token")

    async def test_handles_non_json_response(self):
        result = await reverse_geocode(
            FakeHttpClient(status=502, data="bad gateway"),
            "token",
            {"reverse_geocode_url": "https://geo.example/reverse"},
            39.9,
            116.4,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["errorType"], "network_error")

    async def test_custom_provider_exposes_capability(self):
        provider = CustomProvider()
        result = await provider.reverse_geocode(
            FakeHttpClient(data={"address": "上海市"}),
            "token",
            {"reverseGeocodeUrl": "https://geo.example/reverse"},
            31.23,
            121.47,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["address"], "上海市")


class CustomReverseGeocodeConfigTests(unittest.TestCase):
    def test_loads_and_forwards_reverse_geocode_url(self):
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.ini"
            config_path.write_text(
                "[custom]\nreverse_geocode_url = https://geo.example/reverse\n",
                encoding="utf-8",
            )
            config = _load_custom_from_ini(config_path)

        handler = WebSocketHandler(None, None, None, None, config)
        request_config = handler._build_request_config({}, "custom")

        self.assertEqual(config.reverse_geocode_url, "https://geo.example/reverse")
        self.assertEqual(
            request_config["reverseGeocodeUrl"], "https://geo.example/reverse"
        )


if __name__ == "__main__":
    unittest.main()
