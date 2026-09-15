from __future__ import annotations

from pathlib import Path

from service.app.main import app

ROOT = Path(__file__).resolve().parent
OPS_ADMIN = ROOT / "service/app/routes/ops_admin.py"
OPS_UI = ROOT / "service/app/routes/ops_ui.py"
OPS_JS = ROOT / "service/app/assets/ops-app.js"

paths = app.openapi()["paths"]
required = {
    "/v1/ops/owner/profile",
    "/v1/ops/users",
    "/v1/ops/users/{user_id}",
    "/v1/ops/license-projects",
    "/v1/ops/licenses",
    "/v1/ops/licenses/validate",
    "/v1/ops/licenses/{license_id}/revoke",
    "/v1/ops/plans",
    "/v1/ops/customers",
    "/v1/ops/partners",
    "/v1/ops/stats",
    "/v1/ops/usage",
    "/v1/ops/providers/evolution",
}
missing = sorted(required - paths.keys())
assert not missing, missing

source = OPS_ADMIN.read_text()
assert "def _audit(" in source
assert "metadata_json" in source
assert "token_hash" not in source.split("def _serialize_license", 1)[1].split("def _serialize_customer", 1)[0]
assert "return {\"ok\": True, \"token\": token" in source
assert "password" not in source.split("def _serialize_user", 1)[1].split("def _serialize_profile", 1)[0]

ui = OPS_UI.read_text()
for panel in ("overview", "owner", "users", "customers", "projects", "licenses", "plans", "partners", "whatsapp", "evolution", "stats", "usage", "queues", "alerts", "audit"):
    assert f'data-panel="{panel}"' in ui, panel

bundle = OPS_JS.read_text()
for endpoint in ("/v1/ops/users", "/v1/ops/licenses", "/v1/ops/plans", "/v1/ops/customers", "/v1/ops/partners", "/v1/ops/usage"):
    assert endpoint in bundle, endpoint
assert '"Content-Type": "application/json"' in bundle
assert "credentials: \"same-origin\"" in bundle

print(f"ops_admin_paths={len(required)}")
print("ops_tabs=15")
print("audit_mutations=present")
print("secret_response_guard=pass")
print("ops_admin_contract=pass")
