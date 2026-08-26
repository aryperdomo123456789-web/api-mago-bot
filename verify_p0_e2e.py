from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REQUIRED_PATHS = (
    "/v1/organizations",
    "/v1/integrations",
    "/v1/channels",
    "/v1/messages",
    "/v1/conversations",
    "/v1/billing",
    "/v1/analytics",
    "/v1/jobs",
    "/v1/onboarding",
)


def request(base_url: str, host: str, path: str, method: str = "GET", body: bytes | None = None) -> tuple[int, bytes]:
    req = Request(
        base_url.rstrip("/") + path,
        data=body,
        method=method,
        headers={"Host": host, "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise RuntimeError(f"canary unavailable: {exc.reason}") from exc


def assert_code(base_url: str, host: str, path: str, expected: int) -> None:
    actual, _ = request(base_url, host, path)
    assert actual == expected, f"{host}{path}: expected {expected}, got {actual}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("P0_E2E_BASE_URL", "http://127.0.0.1:4350"))
    args = parser.parse_args()
    base_url = args.base_url
    if "mago-bot.com" in base_url and os.getenv("ALLOW_P0_PROD_E2E", "false").lower() != "true":
        raise SystemExit("refusing public production URL; use the isolated canary or explicitly set ALLOW_P0_PROD_E2E=true")

    assert_code(base_url, "app.mago-bot.com", "/health/ready", 200)
    assert_code(base_url, "app.mago-bot.com", "/v1/organizations", 401)
    assert_code(base_url, "app.mago-bot.com", "/v1/integrations", 401)
    assert_code(base_url, "app.mago-bot.com", "/v1/onboarding?project_id=1", 401)
    assert_code(base_url, "app.mago-bot.com", "/v1/messages?project_id=1", 401)
    assert_code(base_url, "evo-api.mago-bot.com", "/v1/organizations", 404)
    assert_code(base_url, "evo-api.mago-bot.com", "/v1/onboarding?project_id=1", 404)

    openapi_status, openapi_body = request(base_url, "app.mago-bot.com", "/openapi.json")
    assert openapi_status == 200, f"openapi expected 200, got {openapi_status}"
    spec = json.loads(openapi_body)
    missing = [path for path in REQUIRED_PATHS if path not in spec.get("paths", {})]
    assert not missing, f"missing P0 paths: {missing}"
    assert "access_token" not in json.dumps(spec.get("paths", {})) or "ProviderIntegrationCreateRequest" in json.dumps(spec), "credential fields must be write-only or intentionally scoped"
    print("p0_e2e_surface=ok")
    print("p0_e2e_openapi=ok")
    print("p0_e2e_cross_surface=ok")
    print("p0_e2e_auth_fixture=not_run_no_test_credentials")
    return 0


if __name__ == "__main__":
    sys.exit(main())
