from __future__ import annotations

from typing import Any, Iterable


CANONICAL_DOWNSTREAM_EVENTS = frozenset(
    {
        "message.inbound",
        "message.status",
        "connection.updated",
        "qrcode.updated",
    }
)


def _compact(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "").replace("-", "").replace(".", "")


def canonical_event_type(raw_event_type: str, payload: dict[str, Any] | None = None) -> str:
    """Map provider-specific names to the stable downstream M2M contract."""
    raw = str(raw_event_type or "").strip().lower()
    if raw in CANONICAL_DOWNSTREAM_EVENTS:
        return raw
    compact = _compact(raw)
    if compact in {"message", "messages", "messageupsert", "messagesupsert", "inbound", "messagesreceived"}:
        return "message.inbound"
    if compact in {
        "status",
        "statuses",
        "receipt",
        "readreceipt",
        "delivery",
        "deliverystatus",
        "messageack",
        "sendmessage",
        "errors",
        "error",
    }:
        return "message.status"
    if compact in {
        "connection",
        "connectionupdate",
        "connected",
        "pairsuccess",
        "loggedout",
        "offline",
        "offlinesynccompleted",
        "presence",
        "chatpresence",
    }:
        return "connection.updated"
    if compact in {"qrcode", "qrcodeupdated", "qr", "qrupdated", "qrtimeout"}:
        return "qrcode.updated"
    if raw.startswith("message."):
        return "message.status"
    if raw.startswith("connection."):
        return "connection.updated"
    if raw.startswith("qrcode.") or raw.startswith("qr."):
        return "qrcode.updated"
    return raw[:80] or "unknown"


def _legacy_bucket(canonical: str) -> str | None:
    if canonical == "message.inbound":
        return "messages"
    if canonical == "message.status":
        return "statuses"
    if canonical in {"connection.updated", "qrcode.updated"}:
        return "account"
    return None


def subscription_event_matches(events: Iterable[str] | None, canonical: str, raw_event_type: str | None = None) -> bool:
    wanted = {str(item).strip().lower() for item in (events or []) if str(item).strip()}
    if "all" in wanted or canonical.lower() in wanted:
        return True
    legacy = _legacy_bucket(canonical)
    if legacy and legacy in wanted:
        return True
    raw = str(raw_event_type or "").strip().lower()
    return bool(raw and raw in wanted)


def allowed_subscription_events() -> list[str]:
    return sorted(CANONICAL_DOWNSTREAM_EVENTS)
