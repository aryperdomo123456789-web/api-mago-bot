from __future__ import annotations

import logging
import re
import secrets
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .platform_errors import internal_error_response
from .platform_observability import record_request
from .surface_auth import route_surface_status

logger = logging.getLogger("mago.platform")
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")


def _trace_context(request: Request) -> tuple[str, str]:
    incoming = request.headers.get("traceparent", "")
    match = _TRACEPARENT.match(incoming)
    if match and match.group(1) != "0" * 32 and match.group(2) != "0" * 16:
        return match.group(1), secrets.token_hex(8)
    return secrets.token_hex(16), secrets.token_hex(8)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id")
        if not request_id or len(request_id) > 80 or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for char in request_id):
            request_id = secrets.token_urlsafe(16)
        request.state.request_id = request_id
        trace_id, span_id = _trace_context(request)
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        started = time.perf_counter()
        try:
            surface_status = route_surface_status(request)
            if surface_status is not None:
                response = JSONResponse(
                    status_code=surface_status,
                    content={"detail": "not found"},
                    headers={"Cache-Control": "no-store"},
                )
            else:
                response = await call_next(request)
        except Exception:
            logger.exception(
                "unhandled_request_exception",
                extra={"request_id": request_id, "trace_id": trace_id, "method": request.method, "path": request.url.path},
            )
            response = internal_error_response(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        record_request(request.method, request.url.path, response.status_code, elapsed_ms)
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
            },
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        response.headers["traceparent"] = f"00-{trace_id}-{span_id}-01"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self' https://graph.facebook.com; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        return response
