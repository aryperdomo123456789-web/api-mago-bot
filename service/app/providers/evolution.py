from __future__ import annotations

import os
from typing import Any

import httpx

from .base import ProviderError, ProviderMessageResult


class EvolutionAdapter:
    provider_type = "evolution"

    def __init__(self) -> None:
        self.base_url = os.getenv("EVOLUTION_INTERNAL_URL", "http://evolution-api:8080").rstrip("/")
        self.api_key = os.getenv("EVOLUTION_API_KEY", "")
        self.timeout = httpx.Timeout(float(os.getenv("EVOLUTION_HTTP_TIMEOUT", "20")))

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderError("Evolution provider is not configured", code="provider_not_configured")
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def send_message(self, resource_id: str, payload: dict[str, Any]) -> ProviderMessageResult:
        if payload.get("type") != "text" or not isinstance(payload.get("text"), dict):
            raise ProviderError("Evolution adapter currently supports text messages only", code="unsupported_message_type")
        body = {
            "number": payload.get("to"),
            "text": payload["text"].get("body", ""),
        }
        url = f"{self.base_url}/message/sendText/{resource_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self._headers(), json=body)
        except httpx.TimeoutException as exc:
            raise ProviderError("Evolution request timed out", code="provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("Evolution request failed", code="provider_network_error", retryable=True) from exc

        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 500:
            raise ProviderError("Evolution temporary failure", code="provider_5xx", retryable=True)
        if response.status_code >= 400:
            error = data.get("message") if isinstance(data, dict) else None
            raise ProviderError(str(error or "Evolution rejected the message")[:512], code="provider_rejected")
        provider_id = None
        if isinstance(data, dict):
            key = data.get("key")
            provider_id = key.get("id") if isinstance(key, dict) else data.get("id")
        if not provider_id:
            raise ProviderError("Evolution returned no message id", code="provider_invalid_response")
        return ProviderMessageResult(provider_message_id=str(provider_id), raw=data)

    async def health(self) -> bool:
        return bool(self.api_key)
