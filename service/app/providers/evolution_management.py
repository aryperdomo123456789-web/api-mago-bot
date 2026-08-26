from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

from .base import ProviderError


class EvolutionManagementAdapter:
    """Server-side lifecycle adapter for Evolution API v2 and Evolution Go."""

    provider_type = "evolution"

    def __init__(self, flavor: str | None = None) -> None:
        configured = (flavor or os.getenv("EVOLUTION_PROVIDER_FLAVOR", "evolution_api")).strip().lower()
        self.flavor = configured if configured in {"evolution_api", "evolution_go"} else "evolution_api"
        self.base_url = os.getenv("EVOLUTION_INTERNAL_URL", "http://evolution-api:8080").rstrip("/")
        self.api_key = os.getenv("EVOLUTION_API_KEY", "")
        self.timeout = httpx.Timeout(float(os.getenv("EVOLUTION_HTTP_TIMEOUT", "20")))

    def _require_key(self, token: str | None = None) -> str:
        key = token or self.api_key
        if not key:
            raise ProviderError("Evolution provider is not configured", code="provider_not_configured")
        return key

    @staticmethod
    def _path_value(value: str) -> str:
        return quote(value.strip(), safe="")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "apikey": self._require_key(token),
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=headers,
                    params=params,
                    json=json_body,
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("Evolution management request timed out", code="provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("Evolution management request failed", code="provider_network_error", retryable=True) from exc

        try:
            data = response.json()
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {"data": data}
        if response.status_code == 429 or response.status_code >= 500:
            raise ProviderError("Evolution management temporary failure", code="provider_5xx", retryable=True)
        if response.status_code >= 400:
            message = data.get("message") or data.get("error") or "Evolution management request rejected"
            raise ProviderError(str(message)[:512], code="provider_rejected")
        return data

    @staticmethod
    def _data(data: dict[str, Any]) -> dict[str, Any]:
        nested = data.get("data")
        return nested if isinstance(nested, dict) else data

    @staticmethod
    def _safe_provider_payload(data: dict[str, Any]) -> dict[str, Any]:
        blocked = {"token", "instanceToken", "instance_token", "apikey", "apiKey", "secret", "password"}

        def clean(value: Any) -> Any:
            if isinstance(value, dict):
                return {str(key): clean(item) for key, item in value.items() if str(key) not in blocked}
            if isinstance(value, list):
                return [clean(item) for item in value[:100]]
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            return str(value)

        result = clean(data)
        return result if isinstance(result, dict) else {"data": result}

    async def create_instance(self, instance_name: str, instance_token: str) -> dict[str, Any]:
        name = self._path_value(instance_name)
        if self.flavor == "evolution_go":
            body = {"name": instance_name, "token": instance_token}
        else:
            body = {
                "instanceName": instance_name,
                "token": instance_token,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS",
            }
        response = await self._request("POST", "/instance/create", json_body=body)
        return {"created": True, "instance_name": instance_name, "provider": self._safe_provider_payload(response)}

    async def connect(
        self,
        instance_name: str,
        instance_token: str,
        *,
        webhook_url: str | None = None,
        events: list[str] | None = None,
        pairing_phone: str | None = None,
    ) -> dict[str, Any]:
        normalized_events = events or ["ALL"]
        if self.flavor == "evolution_go":
            body: dict[str, Any] = {
                "webhookUrl": webhook_url or "",
                "subscribe": normalized_events,
                "immediate": True,
            }
            if pairing_phone:
                body["phone"] = pairing_phone
            response = await self._request(
                "POST",
                "/instance/connect",
                token=instance_token,
                json_body=body,
                extra_headers={"instanceId": instance_name},
            )
        else:
            response = await self._request("GET", f"/instance/connect/{self._path_value(instance_name)}")
        return self._safe_provider_payload(response)

    async def qr(self, instance_name: str, instance_token: str | None = None) -> dict[str, Any]:
        if self.flavor == "evolution_go":
            response = await self._request("GET", "/instance/qr", token=instance_token)
        else:
            response = await self._request("GET", f"/instance/connect/{self._path_value(instance_name)}")
        data = self._data(response)
        qr_value = data.get("qrcode") or data.get("qr") or data.get("code")
        return {"qrcode": qr_value, "expires_in": int(os.getenv("EVOLUTION_QR_TTL_SECONDS", "60"))}

    async def pair(self, instance_name: str, instance_token: str, phone: str) -> dict[str, Any]:
        if self.flavor != "evolution_go":
            raise ProviderError("Pairing code is not exposed by this Evolution API flavor", code="unsupported_operation")
        response = await self._request(
            "POST",
            "/instance/pair",
            token=instance_token,
            json_body={"phone": phone},
        )
        data = self._data(response)
        return {"pairing_code": data.get("code") or data.get("pairingCode"), "provider": self._safe_provider_payload(response)}

    async def status(self, instance_name: str, instance_token: str | None = None) -> dict[str, Any]:
        if self.flavor == "evolution_go":
            response = await self._request("GET", "/instance/status", token=instance_token)
        else:
            response = await self._request("GET", f"/instance/connectionState/{self._path_value(instance_name)}")
        data = self._data(response)
        raw_status = data.get("state") or data.get("status") or data.get("connectionStatus")
        if raw_status is None and "connected" in data:
            raw_status = "connected" if data.get("connected") else "disconnected"
        status_value = str(raw_status or "unknown").lower()
        if status_value in {"open", "connected", "online", "true"}:
            normalized = "connected"
        elif status_value in {"close", "closed", "disconnected", "offline", "false"}:
            normalized = "disconnected"
        else:
            normalized = "degraded" if status_value not in {"unknown", ""} else "unknown"
        return {
            "status": normalized,
            "provider_status": raw_status,
            "jid": data.get("jid") or data.get("JID"),
            "phone": data.get("phone") or data.get("phoneNumber"),
            "checked": True,
            "provider": self._safe_provider_payload(response),
        }

    async def reconnect(self, instance_name: str, instance_token: str | None = None) -> dict[str, Any]:
        if self.flavor == "evolution_go":
            response = await self._request("POST", "/instance/reconnect", token=instance_token)
        else:
            response = await self._request("POST", f"/instance/restart/{self._path_value(instance_name)}")
        return self._safe_provider_payload(response)

    async def disconnect(self, instance_name: str, instance_token: str | None = None) -> dict[str, Any]:
        if self.flavor == "evolution_go":
            response = await self._request("POST", "/instance/disconnect", token=instance_token)
        else:
            response = await self._request("DELETE", f"/instance/logout/{self._path_value(instance_name)}")
        return self._safe_provider_payload(response)

    async def logout(self, instance_name: str, instance_token: str | None = None) -> dict[str, Any]:
        if self.flavor == "evolution_go":
            response = await self._request("DELETE", "/instance/logout", token=instance_token)
        else:
            response = await self._request("DELETE", f"/instance/logout/{self._path_value(instance_name)}")
        return self._safe_provider_payload(response)

    async def delete(self, instance_name: str) -> dict[str, Any]:
        response = await self._request("DELETE", f"/instance/delete/{self._path_value(instance_name)}")
        return self._safe_provider_payload(response)

    async def health(self, instance_name: str | None = None, instance_token: str | None = None) -> dict[str, Any]:
        if instance_name:
            return await self.status(instance_name, instance_token)
        self._require_key()
        return {"status": "configured", "checked": False}
