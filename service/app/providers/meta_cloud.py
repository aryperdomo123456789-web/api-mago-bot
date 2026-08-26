from __future__ import annotations

import os
from typing import Any

import httpx

from .base import ProviderError, ProviderMessageResult


class MetaCloudAdapter:
    provider_type = "meta_cloud"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("META_GRAPH_BASE_URL", "https://graph.facebook.com")).rstrip("/")
        self.api_version = api_version or os.getenv("META_GRAPH_API_VERSION", "v26.0")
        self.access_token = access_token if access_token is not None else os.getenv("META_SYSTEM_USER_TOKEN", "")
        self.timeout = httpx.Timeout(float(os.getenv("META_HTTP_TIMEOUT", "20")))

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise ProviderError("Meta provider is not configured", code="provider_not_configured")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def send_message(self, resource_id: str, payload: dict[str, Any]) -> ProviderMessageResult:
        body = {"messaging_product": "whatsapp", **payload}
        url = f"{self.base_url}/{self.api_version}/{resource_id}/messages"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self._headers(), json=body)
        except httpx.TimeoutException as exc:
            raise ProviderError("Meta request timed out", code="provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("Meta request failed", code="provider_network_error", retryable=True) from exc

        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 500:
            raise ProviderError("Meta temporary failure", code="provider_5xx", retryable=True)
        if response.status_code >= 400:
            error = data.get("error", {}) if isinstance(data, dict) else {}
            raise ProviderError(
                str(error.get("message") or "Meta rejected the message")[:512],
                code=str(error.get("code") or "provider_rejected"),
                retryable=False,
            )
        messages = data.get("messages") if isinstance(data, dict) else None
        message_id = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
        if not message_id:
            raise ProviderError("Meta returned no message id", code="provider_invalid_response", retryable=False)
        return ProviderMessageResult(provider_message_id=str(message_id), raw=data)

    async def health(self) -> bool:
        return bool(self.access_token)
