from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from typing import Any

import httpx


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_BASE_URL = "https://api.resend.com"


class ResendEmailError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(message)


@dataclass(frozen=True)
class ResendEmailResult:
    provider_message_id: str
    dry_run: bool = False


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if len(normalized) > 255 or not _EMAIL_RE.fullmatch(normalized):
        return None
    return normalized


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class ResendEmailClient:
    def __init__(self, *, api_key: str | None = None, base_url: str | None = None, dry_run: bool | None = None) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("RESEND_API_KEY", "")).strip()
        self.base_url = (base_url or os.getenv("RESEND_API_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        # Fail closed: real delivery must be an explicit production decision.
        self.dry_run = _bool_env("RESEND_DRY_RUN", True) if dry_run is None else dry_run

    async def send(
        self,
        *,
        from_email: str,
        from_name: str,
        to_email: str,
        to_name: str | None,
        reply_to: str | None,
        subject: str,
        html_body: str,
        text_body: str,
        tags: dict[str, str] | None = None,
    ) -> ResendEmailResult:
        normalized_from = normalize_email(from_email)
        normalized_to = normalize_email(to_email)
        normalized_reply_to = normalize_email(reply_to) if reply_to else None
        if not normalized_from or not normalized_to or (reply_to and not normalized_reply_to):
            raise ResendEmailError("invalid_email", "Invalid sender, recipient or reply-to address")
        if not subject.strip() or not html_body.strip() or not text_body.strip():
            raise ResendEmailError("invalid_message", "Email subject and bodies are required")
        if self.dry_run:
            return ResendEmailResult(f"dryrun_{uuid.uuid4().hex}", dry_run=True)
        if not self.api_key:
            raise ResendEmailError("provider_not_configured", "Resend is not configured", retryable=False)

        payload: dict[str, Any] = {
            "from": f"{from_name.strip()[:180]} <{normalized_from}>",
            "to": [normalized_to],
            "subject": subject.strip()[:255],
            "html": html_body,
            "text": text_body,
            "headers": {"X-Mago-Transactional": "true"},
        }
        if to_name:
            payload["to"] = [f"{to_name.strip()[:180]} <{normalized_to}>"]
        if normalized_reply_to:
            payload["reply_to"] = [normalized_reply_to]
        if tags:
            payload["tags"] = [{"name": str(key)[:64], "value": str(value)[:256]} for key, value in tags.items()]

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                response = await client.post(
                    f"{self.base_url}/emails",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "MagoBot-TransactionalEmail/1.0",
                    },
                )
        except httpx.TimeoutException as exc:
            raise ResendEmailError("provider_timeout", "Resend request timed out", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ResendEmailError("provider_network_error", "Resend network request failed", retryable=True) from exc

        if response.status_code >= 400:
            detail = ""
            try:
                data = response.json()
                detail = str(data.get("message") or data.get("error") or "")[:300]
            except ValueError:
                detail = response.text[:300]
            retryable = response.status_code == 429 or response.status_code >= 500
            raise ResendEmailError(
                f"resend_http_{response.status_code}",
                detail or f"Resend rejected the email ({response.status_code})",
                retryable=retryable,
            )

        try:
            data = response.json()
            message_id = str(data.get("id") or "").strip()
        except ValueError as exc:
            raise ResendEmailError("provider_invalid_response", "Resend returned invalid JSON", retryable=True) from exc
        if not message_id:
            raise ResendEmailError("provider_missing_message_id", "Resend returned no email id", retryable=True)
        return ResendEmailResult(message_id)
