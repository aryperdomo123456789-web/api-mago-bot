from __future__ import annotations

import hashlib
import hmac
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.m2m_schemas import M2MChannelCreateRequest, M2MChannelView, M2MWebhookView
from app.platform_limits import get_service_api_key_x_api_key
from app.routes.m2m import _public_provider
from app.surface_auth import route_surface_status
from app.webhook_worker import build_signed_delivery


def request_for(host: str, path: str):
    from starlette.requests import Request

    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(b"host", host.encode())],
        "scheme": "https",
        "server": (host, 443),
        "client": ("198.51.100.10", 50000),
    })


def test_channel_contract_and_surface() -> None:
    payload = M2MChannelCreateRequest(display_name="laboratorio-01", provider="evolution", provider_flavor="evolution_api")
    assert payload.provider == "evolution"
    assert payload.provider_flavor == "evolution_api"
    uuid = "00000000-0000-4000-8000-000000000001"
    path = f"/v1/projects/{uuid}/channels"
    assert route_surface_status(request_for("app.mago-bot.com", path)) is None
    assert route_surface_status(request_for("evo-api.mago-bot.com", path)) == 404


def test_provider_secret_redaction() -> None:
    cleaned = _public_provider({"token": "no", "apikey": "no", "qrcode": "no", "pairingCode": "no", "nested": {"secret": "no", "state": "connected"}})
    assert cleaned == {"nested": {"state": "connected"}}
    for schema in (M2MChannelView, M2MWebhookView):
        assert "token" not in schema.model_fields
        assert "password" not in schema.model_fields


def test_signed_downstream_delivery() -> None:
    event = SimpleNamespace(
        event_uuid=UUID("11111111-1111-4111-8111-111111111111"),
        event_type="MESSAGES_UPSERT",
        provider_type="evolution",
        received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        payload={"event": "MESSAGES_UPSERT", "data": {"text": "opt-in", "message_id": "m-1"}},
    )
    delivery = SimpleNamespace(delivery_uuid=UUID("22222222-2222-4222-8222-222222222222"))
    secret = "whsec_test_only"
    body, headers = build_signed_delivery(event, delivery, secret)
    payload = json.loads(body)
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert payload["type"] == "message.inbound"
    assert headers["X-Mago-Event-ID"] == str(event.event_uuid)
    assert headers["X-Mago-Delivery-ID"] == str(delivery.delivery_uuid)
    assert hmac.compare_digest(headers["X-Mago-Signature"], f"sha256={expected}")


def test_strict_api_key_dependency_shape() -> None:
    assert get_service_api_key_x_api_key.__name__ == "get_service_api_key_x_api_key"
    assert "cookies" not in get_service_api_key_x_api_key.__annotations__


if __name__ == "__main__":
    test_channel_contract_and_surface()
    test_provider_secret_redaction()
    test_signed_downstream_delivery()
    test_strict_api_key_dependency_shape()
    print("VERSIONED_M2M_TESTS=PASS")
