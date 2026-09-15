from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from ..db import engine
from ..platform_observability import metrics_text
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service="pd-api")


@router.get("/health/live")
def liveness():
    return {"status": "ok", "service": "mago-platform", "timestamp": datetime.now(timezone.utc)}


@router.get("/health/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database not ready") from exc
    return {"status": "ready", "database": "ok", "timestamp": datetime.now(timezone.utc)}


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token")):
    expected = os.getenv("METRICS_TOKEN", "")
    if len(expected) < 32 or not x_metrics_token or not hmac.compare_digest(x_metrics_token, expected):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return metrics_text()
