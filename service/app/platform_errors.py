import re
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_CANONICAL_STATUS = {
    400: "INVALID_ARGUMENT",
    401: "UNAUTHENTICATED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    408: "DEADLINE_EXCEEDED",
    409: "ABORTED",
    410: "NOT_FOUND",
    412: "FAILED_PRECONDITION",
    413: "RESOURCE_EXHAUSTED",
    422: "INVALID_ARGUMENT",
    429: "RESOURCE_EXHAUSTED",
    500: "INTERNAL",
    501: "UNIMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "UNAVAILABLE",
    504: "DEADLINE_EXCEEDED",
}
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")
_SAFE_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,79}$")


def request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value)[:80] if value else None


def _safe_code(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if _SAFE_CODE.fullmatch(candidate) else fallback


def _safe_reason(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip().upper()
    return candidate if _SAFE_REASON.fullmatch(candidate) else fallback


def _safe_message(value: Any, fallback: str) -> str:
    message = str(value or fallback).strip()
    return message[:512] or fallback


def _safe_detail(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        allowed = {"code", "message", "reason", "retryable", "retry_after_seconds", "metric", "limit", "status", "provider", "field", "fields"}
        return {str(key): value[key] for key in value if str(key) in allowed and isinstance(value[key], (str, int, float, bool, type(None), list))}
    if isinstance(value, list):
        return [_safe_detail(item) for item in value[:20]]
    return "request failed"


def error_body(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    reason: str | None = None,
    domain: str = "api.mago-bot.com",
    retryable: bool = False,
    retry_after_seconds: int | None = None,
    details: list[dict[str, Any]] | None = None,
    legacy_detail: Any = None,
) -> dict[str, Any]:
    canonical = _CANONICAL_STATUS.get(status_code, "INTERNAL" if status_code >= 500 else "UNKNOWN")
    error = {
        "code": _safe_code(code, "internal_error" if status_code >= 500 else "request_error"),
        "message": _safe_message(message, "A operação não pôde ser concluída." if status_code >= 500 else "A requisição não pôde ser processada."),
        "status": canonical,
        "reason": _safe_reason(reason, canonical),
        "domain": domain[:120],
        "retryable": bool(retryable),
        "request_id": request_id(request),
        "details": details or [],
    }
    if retry_after_seconds is not None and retry_after_seconds > 0:
        error["retry_after_seconds"] = min(int(retry_after_seconds), 86400)
    body = {"error": error}
    if legacy_detail is not None:
        body["detail"] = _safe_detail(legacy_detail)
    return body


def response_for_error(request: Request, body: dict[str, Any], status_code: int, retry_after_seconds: int | None = None) -> JSONResponse:
    headers = {"Cache-Control": "no-store"}
    if retry_after_seconds and retry_after_seconds > 0:
        headers["Retry-After"] = str(min(int(retry_after_seconds), 86400))
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def from_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "request_error")
        message = detail.get("message") or detail.get("detail") or "A requisição não pôde ser processada."
        reason = detail.get("reason")
        retryable = bool(detail.get("retryable", exc.status_code in {408, 429, 502, 503, 504}))
        retry_after = detail.get("retry_after_seconds")
        if retry_after is None and exc.headers:
            try:
                retry_after = int(exc.headers.get("Retry-After", "0")) or None
            except (TypeError, ValueError):
                retry_after = None
        details = detail.get("details") if isinstance(detail.get("details"), list) else []
    else:
        code = "request_error"
        message = detail or "A requisição não pôde ser processada."
        reason = None
        retryable = exc.status_code in {408, 429, 502, 503, 504}
        retry_after = None
        details = []
    body = error_body(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        reason=reason,
        retryable=retryable,
        retry_after_seconds=retry_after,
        details=details,
        legacy_detail=detail,
    )
    return response_for_error(request, body, exc.status_code, retry_after)


def from_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for item in exc.errors()[:20]:
        location = ".".join(str(part) for part in item.get("loc", []))
        details.append({"type": "field_violation", "field": location, "message": _safe_message(item.get("msg"), "invalid value")})
    body = error_body(
        request,
        status_code=422,
        code="invalid_argument",
        message="Um ou mais campos da requisição são inválidos.",
        reason="INVALID_ARGUMENT",
        details=details,
        legacy_detail=details,
    )
    return response_for_error(request, body, 422)


def internal_error_response(request: Request) -> JSONResponse:
    body = error_body(
        request,
        status_code=500,
        code="internal_error",
        message="A operação não pôde ser concluída.",
        reason="INTERNAL_ERROR",
    )
    return response_for_error(request, body, 500)
