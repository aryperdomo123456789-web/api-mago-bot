from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from ..core.config import Settings

router = APIRouter(tags=["public"])
settings = Settings()
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
BRAND_LOGO_PATH = ASSETS_DIR / "mago-logo-192.png"
FAVICON_PATH = ASSETS_DIR / "mago-favicon.png"
SHARE_CARD_PATH = ASSETS_DIR / "share-card-ui-20260805.png"
HERO_IMAGE_PATH = ASSETS_DIR / "mago-hero-20260826.png"
CTA_IMAGE_PATH = ASSETS_DIR / "mago-cta-human-20260826.png"

PUBLIC_APP_JS = r'''(() => {
  const button = document.querySelector('[data-nav-toggle]');
  const menu = document.querySelector('.nav-links');
  if (!button || !menu) return;

  const setOpen = (open) => {
    menu.dataset.open = String(open);
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  };

  button.addEventListener('click', () => setOpen(menu.dataset.open !== 'true'));
  menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => setOpen(false)));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setOpen(false);
  });
  document.addEventListener('click', (event) => {
    if (menu.dataset.open === 'true' && !menu.contains(event.target) && !button.contains(event.target)) setOpen(false);
  });
})();'''

API_REFERENCE = {
    "service": "API Mago Bot — Produto de API",
    "base_url": settings.public_base_url,
    "docs": {
        "openapi": "/docs",
        "redoc": "/redoc",
        "catalog": "/v1/info",
        "reference": "/v1/reference",
    },
    "flows": [
        {
            "name": "Criar projeto",
            "request": {
                "method": "POST",
                "path": "/v1/projects",
                "auth": "x-admin-token",
                "body": {
                    "name": "Cliente Elite",
                    "slug": "cliente-elite",
                    "domain": "app.cliente.com",
                    "description": "Projeto do cliente Elite",
                },
            },
        },
        {
            "name": "Emitir licença",
            "request": {
                "method": "POST",
                "path": "/v1/keys",
                "auth": "x-admin-token",
                "body": {
                    "label": "Licença Cliente Elite",
                    "project_slug": "cliente-elite",
                    "scopes": ["whatsapp:connect", "whatsapp:send", "whatsapp:webhook"],
                    "created_by": "admin",
                },
            },
        },
        {
            "name": "Validar licença",
            "request": {
                "method": "POST",
                "path": "/v1/keys/validate",
                "body": {
                    "token": "CHAVE_RECEBIDA",
                    "project_slug": "cliente-elite",
                    "scope": "whatsapp:connect",
                    "domain": "app.cliente.com",
                },
            },
        },
        {
            "name": "Revogar licença",
            "request": {
                "method": "POST",
                "path": "/v1/keys/{id}/revoke",
                "auth": "x-admin-token",
            },
        },
    ],
    "supported_scopes": [
        {"scope": "whatsapp:connect", "description": "Autoriza conexão e pareamento da conta WhatsApp."},
        {"scope": "whatsapp:send", "description": "Autoriza envio de mensagens e mídia pela API."},
        {"scope": "whatsapp:webhook", "description": "Autoriza a camada de webhook/eventos da instância."},
        {"scope": "license:read", "description": "Autoriza consulta de status e auditoria da licença."},
        {"scope": "license:write", "description": "Autoriza emissão, edição e revogação de licenças."},
    ],
}


@router.get("/public-app.js")
def public_app_js():
    return Response(PUBLIC_APP_JS, media_type="application/javascript")


@router.get("/v1/reference")
def public_reference():
    return API_REFERENCE


@router.get("/v1/scopes")
def public_scopes():
    return {"items": API_REFERENCE["supported_scopes"]}


@router.get("/brand-logo.png")
def brand_logo():
    return Response(BRAND_LOGO_PATH.read_bytes(), media_type="image/png")


@router.get("/brand-logo-ui.png")
def brand_logo_ui():
    return Response(BRAND_LOGO_PATH.read_bytes(), media_type="image/png")


@router.get("/share-card.png")
def share_card():
    return Response(SHARE_CARD_PATH.read_bytes(), media_type="image/png")


@router.get("/share-card-ui.png")
def share_card_ui():
    return Response(SHARE_CARD_PATH.read_bytes(), media_type="image/png")


@router.get("/favicon.ico")
def favicon():
    return Response(FAVICON_PATH.read_bytes(), media_type="image/png")


@router.get("/mago-hero.png")
def mago_hero():
    return Response(HERO_IMAGE_PATH.read_bytes(), media_type="image/png")


@router.get("/mago-cta-human.png")
def mago_cta_human():
    return Response(CTA_IMAGE_PATH.read_bytes(), media_type="image/png")


@router.get("/", response_class=HTMLResponse)
def public_home():
    template = (ASSETS_DIR / "public-home.html").read_text(encoding="utf-8")
    html = template.replace("__PUBLIC_BASE_URL__", settings.public_base_url)
    return HTMLResponse(html)


@router.get("/v1/info")
def public_info():
    return {
        "service": settings.app_name,
        "product_name": "API Mago Bot — Produto de API",
        "status": "ok",
        "version": "0.3.0",
        "base_url": settings.public_base_url,
        "admin_url": "/admin",
        "documentation_url": "/docs",
        "reference_url": "/v1/reference",
        "scopes_url": "/v1/scopes",
        "api": {
            "projects": ["/v1/projects", "/v1/licenses/projects"],
            "keys": ["/v1/keys", "/v1/licenses"],
            "validate": ["/v1/keys/validate", "/v1/licenses/validate"],
            "revoke": ["/v1/keys/{id}/revoke", "/v1/licenses/{id}/revoke"],
            "plans": ["/v1/plans"],
            "trials": ["/v1/trials", "/v1/trials/activate"],
            "partners": ["/v1/partners/apply"],
        },
        "auth": {
            "admin_header": "x-admin-token",
            "client_validation": "license token",
        },
        "scopes": list(settings.allowed_scopes),
        "supported_use_cases": [
            "whatsapp:connect",
            "whatsapp:send",
            "whatsapp:webhook",
            "license:read",
            "license:write",
        ],
        "product": {
            "product_name": "API Mago Bot — Produto de API",
            "positioning": "API multi-tenant para mensageria, automação e operação de canais com providers separados",
        },
    }
