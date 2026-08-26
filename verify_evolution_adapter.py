from __future__ import annotations

import asyncio
from unittest.mock import patch

from service.app.providers.base import ProviderError
from service.app.providers.evolution import EvolutionAdapter
from service.app.providers.evolution_management import EvolutionManagementAdapter


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeClient:
    requests = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method, url, **kwargs):
        FakeClient.requests.append((method, url, kwargs))
        return FakeResponse({"data": {"state": "open", "key": {"id": "msg-1"}, "token": "must-not-escape"}})

    async def post(self, url, **kwargs):
        FakeClient.requests.append(("POST", url, kwargs))
        return FakeResponse({"key": {"id": "msg-1"}})


async def main():
    with patch("service.app.providers.evolution.httpx.AsyncClient", FakeClient):
        adapter = EvolutionAdapter(api_key="test-key", flavor="evolution_api")
        result = await adapter.send_message("inst-a", {"to": "5511999999999", "type": "text", "text": {"body": "oi"}})
        assert result.provider_message_id == "msg-1"
        assert FakeClient.requests[-1][1].endswith("/message/sendText/inst-a")
        media_result = await adapter.send_message("inst-a", {"to": "5511999999999", "type": "image", "media": {"type": "image", "url": "https://cdn.example.com/image.png", "caption": "teste"}})
        assert media_result.provider_message_id == "msg-1"
        try:
            await adapter.send_message("inst-a", {"to": "5511999999999", "type": "image", "media": {"type": "image", "url": "http://127.0.0.1/image.png"}})
        except ProviderError as exc:
            assert exc.code == "invalid_media_url"
        else:
            raise AssertionError("private HTTP media URL must be rejected")

    with patch("service.app.providers.evolution_management.httpx.AsyncClient", FakeClient):
        management = EvolutionManagementAdapter(flavor="evolution_go")
        management.api_key = "global-key"
        created = await management.create_instance("inst-a", "instance-secret")
        assert created["created"] is True
        assert "token" not in str(created)
        status = await management.status("inst-a", "instance-secret")
        assert status["status"] == "connected"
        assert "token" not in str(status)


asyncio.run(main())
print("evolution adapter tests ok")
