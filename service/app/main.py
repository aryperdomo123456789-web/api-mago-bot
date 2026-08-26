import fcntl
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .auth import hash_password
from .core.config import Settings
from .db import Base, engine
from .models import CustomerAccount, LicenseAuditLog, LicenseKey, LicenseProject, OwnerProfile, PanelUser, PartnerApplication, PlanCatalog  # noqa: F401
from .routes.account import router as account_router
from .routes.admin import router as admin_router
from .routes.health import router as health_router
from .routes.licenses import router as licenses_router
from .routes.product import router as product_router
from .routes.public import router as public_router

app = FastAPI(title="WhatsApp API Licensing", version="0.2.0")
settings = Settings()
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.on_event("startup")
def startup():
    lock_path = "/tmp/licensing_central_startup.lock"
    with open(lock_path, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
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
app.include_router(admin_router)
