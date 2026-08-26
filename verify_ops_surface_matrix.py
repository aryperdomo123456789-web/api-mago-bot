from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from service.app.surface_auth import route_surface_status


def make_request(path: str, host: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(b"host", host.encode())],
        "client": ("127.0.0.1", 50000),
        "server": (host, 443),
        "scheme": "https",
    }
    return Request(scope, receive=lambda: None)


def assert_allowed(path: str, host: str) -> None:
    result = route_surface_status(make_request(path, host))
    assert result is None, (path, host, result)


def assert_denied(path: str, host: str) -> None:
    result = route_surface_status(make_request(path, host))
    assert result == 404, (path, host, result)


for path in ("/ops", "/v1/ops/users", "/v1/ops/licenses", "/v1/ops/plans", "/v1/ops/partners", "/v1/ops/providers/evolution", "/v1/platform/owner/whatsapp", "/v1/account", "/v1/users", "/v1/licenses", "/v1/projects", "/v1/keys", "/v1/trials", "/v1/partners/applications"):
    assert_allowed(path, "evo-api.mago-bot.com")
    assert_denied(path, "app.mago-bot.com")

for path in ("/admin", "/platform", "/v1/platform/projects", "/v1/platform/conversations"):
    assert_allowed(path, "app.mago-bot.com")
    assert_denied(path, "evo-api.mago-bot.com")

print("surface_matrix=pass")
