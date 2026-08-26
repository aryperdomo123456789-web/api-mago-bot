from __future__ import annotations

import uuid
from typing import Any

from .base import ProviderAdapter, ProviderMessageResult


class DryRunAdapter(ProviderAdapter):
    """Provider local para testes de contrato; nunca executa rede nem envia mensagem."""

    async def send_message(self, resource_id: str, payload: dict[str, Any]) -> ProviderMessageResult:
        return ProviderMessageResult(
            provider_message_id=f"dryrun-{uuid.uuid4()}",
            raw={"dry_run": True, "resource_id": resource_id, "type": payload.get("type")},
        )

    async def health(self) -> bool:
        return True
