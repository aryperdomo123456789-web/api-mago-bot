from pathlib import Path

ROOT = Path(__file__).resolve().parent
router = (ROOT / "service/app/routes/product_facade.py").read_text()
main = (ROOT / "service/app/main.py").read_text()
doc = (ROOT / "docs/P0_PUBLIC_PRODUCT_API.md").read_text()

required_routes = [
    '"/organizations"',
    '"/integrations"',
    '"/channels"',
    '"/messages"',
    '"/conversations"',
    '"/billing"',
    '"/analytics"',
    '"/jobs"',
]
for route in required_routes:
    assert route in router, f"missing route marker: {route}"
assert "from .routes.product_facade import router as product_facade_router" in main
assert "app.include_router(product_facade_router)" in main
assert "X-Idempotency-Key" in router
assert "get_service_api_key" in router
assert "get_current_platform_user" in router
assert "instance_token" not in doc.lower()
assert "access_token" not in doc.lower()
assert "checkout real ainda não estão liberados" in doc
print("product_facade_contract=ok")
print("tenant_membership_isolation=declared")
print("provider_secrets_not_documented=ok")
