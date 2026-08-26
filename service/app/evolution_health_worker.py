from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .db import SessionLocal
from .platform_crypto import decrypt_secret
from .platform_models import EvolutionInstance, ProviderResource
from .providers.base import ProviderError
from .providers.evolution_management import EvolutionManagementAdapter

POLL_SECONDS = float(os.getenv("EVOLUTION_HEALTH_POLL_SECONDS", "30"))
CHECK_INTERVAL_SECONDS = int(os.getenv("EVOLUTION_HEALTH_CHECK_INTERVAL_SECONDS", "45"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _due(row: EvolutionInstance) -> bool:
    return not row.last_status_check_at or row.last_status_check_at <= _now() - timedelta(seconds=CHECK_INTERVAL_SECONDS)


async def poll_once() -> bool:
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(EvolutionInstance)
            .where(EvolutionInstance.status.not_in(("deleted", "suspended", "logged_out")))
            .order_by(EvolutionInstance.id)
            .limit(100)
        ).all()
        rows = [row for row in rows if _due(row)]
        if not rows:
            return False
        for row in rows:
            try:
                token = decrypt_secret(row.instance_token_encrypted) if row.instance_token_encrypted else None
                result = await EvolutionManagementAdapter(row.provider_flavor).status(row.instance_name, token)
                row.status = result.get("status") or "degraded"
                row.jid = result.get("jid") or row.jid
                row.display_phone_number = result.get("phone") or row.display_phone_number
                row.last_status_check_at = _now()
                if row.status == "connected":
                    row.last_connected_at = row.last_connected_at or _now()
                    row.last_error_code = None
                    row.last_error_message = None
                if row.resource_id:
                    resource = db.get(ProviderResource, row.resource_id)
                    if resource:
                        resource.status = "active" if row.status == "connected" else "degraded"
            except ProviderError as exc:
                row.status = "degraded"
                row.last_status_check_at = _now()
                row.last_error_code = exc.code
                row.last_error_message = str(exc)[:512]
            except Exception as exc:
                row.status = "degraded"
                row.last_status_check_at = _now()
                row.last_error_code = "health_worker_error"
                row.last_error_message = str(exc)[:512]
        db.commit()
        return True
    finally:
        db.close()


async def run_worker() -> None:
    heartbeat = Path(os.getenv("EVOLUTION_HEALTH_WORKER_HEARTBEAT", "/tmp/mago_evolution_health_worker_heartbeat"))
    while True:
        heartbeat.touch()
        await poll_once()
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker())
