from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ProviderError(Exception):
    def __init__(self, message: str, *, code: str = "provider_error", retryable: bool = False) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(message)


@dataclass(frozen=True)
class ProviderMessageResult:
    provider_message_id: str
    raw: dict[str, Any]


class ProviderAdapter(Protocol):
    provider_type: str

    async def send_message(self, resource_id: str, payload: dict[str, Any]) -> ProviderMessageResult:
        ...

    async def health(self) -> bool:
        ...
