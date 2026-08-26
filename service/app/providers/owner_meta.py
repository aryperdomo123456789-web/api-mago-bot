from __future__ import annotations

import os
from typing import Any

import httpx


class OwnerMetaError(RuntimeError):
    def __init__(self, message: str, code: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class OwnerMetaCloudClient:
    provider_type = "meta_cloud"

    def __init__(self, access_token: str) -> None:
        self.access_token = access_token
        self.base_url = os.getenv("META_GRAPH_BASE_URL", "https://graph.facebook.com").rstrip("/")
        self.api_version = os.getenv("META_GRAPH_API_VERSION", "v26.0")
        self.timeout = httpx.Timeout(float(os.getenv("META_HTTP_TIMEOUT", "20")))

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise OwnerMetaError("Meta token ausente no servidor", "provider_not_configured")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def get_phone_profile(self, phone_number_id: str) -> dict[str, Any]:
        fields = "id,display_phone_number,verified_name,quality_rating,webhook_configuration"
        url = f"{self.base_url}/{self.api_version}/{phone_number_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.get(url, headers=self._headers(), params={"fields": fields})
        except httpx.TimeoutException as exc:
            raise OwnerMetaError("Meta excedeu o tempo de resposta", "provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise OwnerMetaError("Não foi possível alcançar a Meta", "provider_network_error", retryable=True) from exc
        return self._decode_response(response, "Meta rejeitou a consulta do número")

    async def send_template(
        self,
        phone_number_id: str,
        recipient_phone: str,
        template_name: str,
        template_language: str,
        body_parameters: list[str] | None = None,
    ) -> dict[str, Any]:
        template: dict[str, Any] = {
            "name": template_name,
            "language": {"code": template_language},
        }
        if body_parameters:
            template["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": value} for value in body_parameters],
            }]
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "template",
            "template": template,
        }
        url = f"{self.base_url}/{self.api_version}/{phone_number_id}/messages"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.post(url, headers=self._headers(), json=body)
        except httpx.TimeoutException as exc:
            raise OwnerMetaError("Meta excedeu o tempo de resposta", "provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise OwnerMetaError("Não foi possível alcançar a Meta", "provider_network_error", retryable=True) from exc
        return self._decode_response(response, "Meta rejeitou a mensagem de boas-vindas")

    @staticmethod
    def _decode_response(response: httpx.Response, fallback: str) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 500:
            raise OwnerMetaError("Meta informou uma falha temporária", "provider_5xx", retryable=True)
        if response.status_code >= 400:
            error = data.get("error", {}) if isinstance(data, dict) else {}
            message = str(error.get("message") or fallback)[:512]
            code = str(error.get("code") or "provider_rejected")[:80]
            raise OwnerMetaError(message, code, retryable=False)
        if not isinstance(data, dict):
            raise OwnerMetaError("Meta retornou resposta inválida", "provider_invalid_response")
        return data
