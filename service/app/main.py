import fcntl
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .auth import hash_password
from .core.config import Settings
from .db import Base, engine
from .models import CustomerAccount, LicenseAuditLog, LicenseKey, LicenseProject, OwnerProfile, PanelUser, PartnerApplication, PlanCatalog  # noqa: F401
from . import platform_models  # noqa: F401
from .platform_http import SecurityHeadersMiddleware
from .routes.account import router as account_router
from .routes.admin import router as admin_router
from .routes.health import router as health_router
from .routes.licenses import router as licenses_router
from .routes.product import router as product_router
from .routes.public import router as public_router
from .routes.platform import router as platform_router
from .routes.api_keys import router as api_keys_router
from .routes.messages import router as messages_router
from .routes.webhooks import router as webhooks_router
from .routes.resources import router as resources_router
from .routes.platform_ui import router as platform_ui_router
from .routes.usage import router as usage_router
from .routes.webhook_subscriptions import router as webhook_subscriptions_router
from .routes.conversations import router as conversations_router
from .routes.portal_conversations import router as portal_conversations_router
from .routes.owner_whatsapp import router as owner_whatsapp_router
from .routes.ops import router as ops_router
from .routes.ops_admin import router as ops_admin_router
from .routes.ops_ui import router as ops_ui_router
from .routes.mfa import router as mfa_router
from .routes.email_webhooks import router as email_webhooks_router
from .routes.email_ops import router as email_ops_router
from .routes.evolution_management import router as evolution_management_router
from .routes.evolution_webhooks import router as evolution_webhooks_router
from .routes.product_facade import router as product_facade_router
from .routes.provider_integrations import router as provider_integrations_router
from .routes.onboarding import router as onboarding_router
from .routes.channels_public import router as channels_public_router
from .routes.inbox import router as inbox_router

app = FastAPI(
    title="Mago Bot Platform",
    version="1.2.0-alpha.1",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(SecurityHeadersMiddleware)
settings = Settings()


@app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
def self_hosted_docs() -> HTMLResponse:
    html = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mago Bot Platform - Swagger UI</title>
  <link rel="stylesheet" href="/assets/swagger/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="/assets/swagger/swagger-ui-bundle.js" defer></script>
  <script src="/assets/swagger/swagger-init.js" defer></script>
</body>
</html>"""
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.on_event("startup")
def startup():
    lock_path = "/tmp/licensing_central_startup.lock"
    with open(lock_path, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            if os.getenv("PLATFORM_AUTO_CREATE_SCHEMA", "false").lower() == "true":
                Base.metadata.create_all(bind=engine)

            from .db import SessionLocal

            db = SessionLocal()
            try:
                profile = db.get(OwnerProfile, 1)
                if not profile:
                    db.add(
                        OwnerProfile(
                            id=1,
                            display_name=settings.owner_name,
                            email=settings.owner_email,
                        )
                    )
                owner = db.scalar(select(PanelUser).where(PanelUser.email == settings.owner_email))
                if not owner:
                    salt, digest = hash_password(settings.owner_password)
                    db.add(
                        PanelUser(
                            email=settings.owner_email,
                            password_salt=salt,
                            password_hash=digest,
                            full_name=settings.owner_name,
                            role="owner",
                        )
                    )
                if not db.scalar(select(PlanCatalog).limit(1)):
                    db.add_all(
                        [
                            PlanCatalog(
                                slug="start",
                                name="PD Start",
                                subtitle="Entrada leve para testar e validar o produto",
                                description="Plano de entrada para experimentação, onboarding e primeiros clientes.",
                                price_cents=4990,
                                trial_days=7,
                                billing_period_days=30,
                                max_instances=1,
                                max_projects=1,
                                max_keys=3,
                                cta_label="Começar grátis",
                                features=["1 instância", "10k eventos/mês", "webhooks básicos", "suporte padrão"],
                                sort_order=10,
                            ),
                            PlanCatalog(
                                slug="pro",
                                name="PD Pro",
                                subtitle="Operação séria com múltiplos clientes",
                                description="Camada profissional para assinantes com mais volume e automação.",
                                price_cents=9990,
                                trial_days=7,
                                billing_period_days=30,
                                max_instances=5,
                                max_projects=10,
                                max_keys=20,
                                cta_label="Ativar Pro",
                                features=["Até 5 instâncias", "100k eventos/mês", "filas e webhooks", "auditoria completa"],
                                sort_order=20,
                            ),
                            PlanCatalog(
                                slug="elite",
                                name="PD Elite",
                                subtitle="Para parceiros e operação grande",
                                description="Plano avançado com limites personalizados, suporte e SLA.",
                                price_cents=None,
                                trial_days=14,
                                billing_period_days=30,
                                max_instances=None,
                                max_projects=None,
                                max_keys=None,
                                is_partner=True,
                                cta_label="Falar com vendas",
                                features=["instâncias dedicadas", "quota personalizada", "suporte avançado", "integrações enterprise"],
                                sort_order=30,
                            ),
                        ]
                    )
                db.commit()
            finally:
                db.close()
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)


app.include_router(health_router)
app.include_router(public_router)
app.include_router(product_router)
app.include_router(account_router)
app.include_router(licenses_router)
app.include_router(platform_ui_router)
app.include_router(admin_router)
app.include_router(platform_router)
app.include_router(api_keys_router)
app.include_router(messages_router)
app.include_router(webhooks_router)
app.include_router(resources_router)
app.include_router(usage_router)
app.include_router(webhook_subscriptions_router)
app.include_router(conversations_router)
app.include_router(portal_conversations_router)
app.include_router(owner_whatsapp_router)
app.include_router(ops_router)
app.include_router(ops_admin_router)
app.include_router(ops_ui_router)
app.include_router(mfa_router)
app.include_router(email_webhooks_router)
app.include_router(email_ops_router)
app.include_router(evolution_management_router)
app.include_router(evolution_webhooks_router)
app.include_router(product_facade_router)
app.include_router(provider_integrations_router)
app.include_router(onboarding_router)
app.include_router(channels_public_router)
app.include_router(inbox_router)
