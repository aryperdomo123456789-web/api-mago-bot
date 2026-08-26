from __future__ import annotations

import os
from typing import Any

import httpx

from .base import ProviderError, ProviderMessageResult


class EvolutionAdapter:
    provider_type = "evolution"

    def __init__(self, *, api_key: str | None = None, flavor: str | None = None) -> None:
        configured = (flavor or os.getenv("EVOLUTION_PROVIDER_FLAVOR", "evolution_api")).strip().lower()
        self.flavor = configured if configured in {"evolution_api", "evolution_go"} else "evolution_api"
        self.base_url = os.getenv("EVOLUTION_INTERNAL_URL", "http://evolution-api:8080").rstrip("/")
        self.api_key = api_key or os.getenv("EVOLUTION_API_KEY", "")
        self.timeout = httpx.Timeout(float(os.getenv("EVOLUTION_HTTP_TIMEOUT", "20")))

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderError("Evolution provider is not configured", code="provider_not_configured")
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.post(f"{self.base_url}{path}", headers=self._headers(), json=body)
        except httpx.TimeoutException as exc:
            raise ProviderError("Evolution request timed out", code="provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("Evolution request failed", code="provider_network_error", retryable=True) from exc

        try:
            data = response.json()
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {"data": data}
        if response.status_code == 429 or response.status_code >= 500:
            raise ProviderError("Evolution temporary failure", code="provider_5xx", retryable=True)
        if response.status_code >= 400:
            error = data.get("message") or data.get("error")
            raise ProviderError(str(error or "Evolution rejected the message")[:512], code="provider_rejected")
        return data

    @staticmethod
    def _provider_message_id(data: dict[str, Any]) -> str | None:
        nested = data.get("data") if isinstance(data.get("data"), dict) else data
        key = nested.get("key") if isinstance(nested, dict) else None
        if isinstance(key, dict) and key.get("id"):
            return str(key["id"])
        for key_name in ("id", "messageId", "message_id"):
            if isinstance(nested, dict) and nested.get(key_name):
                return str(nested[key_name])
        return None

    async def send_message(self, resource_id: str, payload: dict[str, Any]) -> ProviderMessageResult:
        message_type = str(payload.get("type") or "text").lower()
        if message_type == "text":
            text = payload.get("text")
            if not isinstance(text, dict) or not str(text.get("body") or "").strip():
                raise ProviderError("text.body is required", code="invalid_message_payload")
            if self.flavor == "evolution_go":
                path = "/send/text"
                body = {"number": payload.get("to"), "text": str(text["body"])}
            else:
                path = f"/message/sendText/{resource_id}"
                body = {"number": payload.get("to"), "text": str(text["body"])}
        elif message_type in {"image", "video", "audio", "document", "sticker", "media"}:
            media = payload.get("media")
            if not isinstance(media, dict):
                raise ProviderError("media object is required", code="invalid_message_payload")
            media_type = str(media.get("type") or media.get("media_type") or message_type).lower()
            if media_type == "media":
                media_type = "document"
            if media_type not in {"image", "video", "audio", "document", "sticker"}:
                raise ProviderError("unsupported media type", code="unsupported_message_type")
            media_value = media.get("url") or media.get("base64") or media.get("source") or media.get("data")
            if not isinstance(media_value, str) or not media_value.strip():
                raise ProviderError("media.url or media.base64 is required", code="invalid_message_payload")
            caption = str(media.get("caption") or "")
            filename = str(media.get("filename") or media.get("file_name") or "")
            if self.flavor == "evolution_go":
                path = "/send/media"
                body = {
                    "number": payload.get("to"),
                    "url": media_value,
                    "type": media_type,
                    "caption": caption,
                    "filename": filename,
                }
            else:
                path = f"/message/sendMedia/{resource_id}"
                body = {
                    "number": payload.get("to"),
                    "mediatype": media_type,
                    "media": media_value,
                    "caption": caption,
                    "fileName": filename,
                }
        else:
            raise ProviderError("Evolution adapter supports text and media messages", code="unsupported_message_type")

        data = await self._post(path, body)
        provider_id = self._provider_message_id(data)
        if not provider_id:
            raise ProviderError("Evolution returned no message id", code="provider_invalid_response")
        return ProviderMessageResult(provider_message_id=provider_id, raw=data)

    async def health(self) -> bool:
        return bool(self.api_key)
