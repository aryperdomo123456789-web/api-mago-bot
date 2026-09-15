from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
required = [
    ROOT / "service/app/providers/evolution.py",
    ROOT / "service/app/providers/evolution_management.py",
    ROOT / "service/app/routes/evolution_management.py",
    ROOT / "service/app/routes/evolution_webhooks.py",
    ROOT / "service/app/evolution_schemas.py",
    ROOT / "service/app/evolution_health_worker.py",
    ROOT / "service/app/platform_models.py",
    ROOT / "service/app/main.py",
]
for path in required:
    ast.parse(path.read_text())

migration = (ROOT / "service/sql/migrations/0008_evolution_instances.sql").read_text()
for token in ("evolution_instances", "evolution_instance_events", "0008_evolution_instances", "instance_token_encrypted", "webhook_secret_encrypted"):
    assert token in migration, token

main = (ROOT / "service/app/main.py").read_text()
assert "evolution_management_router" in main
assert "evolution_webhooks_router" in main

management = (ROOT / "service/app/routes/evolution_management.py").read_text()
for path in ("/instances", "/connect", "/qr", "/pair", "/status", "/reconnect", "/disconnect", "/logout"):
    assert path in management, path
assert "decrypt_secret" in management
assert "encrypt_secret" in management
assert "EvolutionManagementAdapter" in management

webhooks = (ROOT / "service/app/routes/evolution_webhooks.py").read_text()
assert "hmac.compare_digest" in webhooks
assert "instanceToken" in webhooks
assert "WebhookDelivery" in webhooks
assert "ConversationEvent" in webhooks

adapter = (ROOT / "service/app/providers/evolution.py").read_text()
assert "sendMedia" in adapter
assert "evolution_go" in adapter
assert "provider_timeout" in adapter

nginx = (ROOT / "service/deploy/nginx/evo-api.mago-bot.com.proxy.conf").read_text()
assert "^~ /v1/webhooks/evolution/" in nginx

for compose_path, service_name in [
    (ROOT / "service/deploy/docker-compose.staging.yml", "evolution-health-worker-canary"),
    (ROOT / "service/deploy/docker-compose.production.yml", "evolution-health-worker"),
]:
    compose = compose_path.read_text()
    assert service_name in compose, service_name
    assert "app.evolution_health_worker" in compose, compose_path

messages = (ROOT / "service/app/routes/messages.py").read_text()
assert "managed_evolution" in messages
assert "evolution_instance_not_connected" in messages
assert "decrypt_secret" in messages
assert "EvolutionAdapter(api_key=api_key, flavor=flavor)" in messages

worker = (ROOT / "service/app/evolution_health_worker.py").read_text()
assert "EVOLUTION_HEALTH_WORKER_HEARTBEAT" in worker
assert "last_status_check_at" in worker

print("evolution contract ok")
