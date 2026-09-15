from __future__ import annotations

import os
import threading
from collections import Counter

_lock = threading.Lock()
_request_counts: Counter[str] = Counter()
_request_latencies_ms: Counter[str] = Counter()


def record_request(method: str, path: str, status_code: int, elapsed_ms: int) -> None:
    key = f"{method} {path} {status_code}"
    with _lock:
        _request_counts[key] += 1
        _request_latencies_ms[path] += max(0, elapsed_ms)


def metrics_token_configured() -> bool:
    token = os.getenv("METRICS_TOKEN", "")
    return len(token) >= 32


def metrics_text() -> str:
    lines = [
        "# HELP mago_http_requests_total Total HTTP responses by method, path and status.",
        "# TYPE mago_http_requests_total counter",
    ]
    with _lock:
        for key, value in sorted(_request_counts.items()):
            method, path, status_code = key.split(" ", 2)
            lines.append(f'mago_http_requests_total{{method="{method}",path="{path}",status="{status_code}"}} {value}')
        lines.extend([
            "# HELP mago_http_request_latency_ms_total Sum of request latency in milliseconds by path.",
            "# TYPE mago_http_request_latency_ms_total counter",
        ])
        for path, value in sorted(_request_latencies_ms.items()):
            lines.append(f'mago_http_request_latency_ms_total{{path="{path}"}} {value}')
    return "\n".join(lines) + "\n"
