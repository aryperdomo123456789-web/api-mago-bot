from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..surface_auth import require_customer_surface

router = APIRouter(tags=["platform-ui"])
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


@router.get("/platform", response_class=HTMLResponse)
@router.get("/admin", response_class=HTMLResponse)
def platform_ui(request: Request) -> HTMLResponse:
    require_customer_surface(request)
    html = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Mago Bot Control Plane — infraestrutura omnichannel de conversas para operações profissionais." />
  <title>Mago Bot | Control Plane</title>
  <link rel="stylesheet" href="/assets/platform.css" />
</head>
<body>
  <div class="noise" aria-hidden="true"></div>
  <main id="app-shell" class="app-shell">
    <section id="auth-view" class="auth-layout" aria-labelledby="auth-title">
      <div class="auth-story">
        <div class="brand-lockup"><span class="brand-mark">M</span><span>MAGO BOT</span></div>
        <div class="story-copy">
          <p class="eyebrow">CONTROL PLANE / WHATSAPP API</p>
          <h1>Infraestrutura de conversa para quem cansou de depender de gambiarra.</h1>
          <p class="story-text">Orquestre projetos, providers, chaves, quotas e webhooks num único cockpit. Transparência no provider. Controle no tenant. Operação pronta para crescer.</p>
        </div>
        <div class="story-grid">
          <div><strong>01</strong><span>API própria</span></div>
          <div><strong>02</strong><span>Meta Cloud ready</span></div>
          <div><strong>03</strong><span>Tenant isolado</span></div>
        </div>
      </div>
      <div class="auth-card-wrap">
        <div class="auth-card">
          <div class="auth-heading">
            <p class="eyebrow">ACESSO OPERACIONAL</p>
            <h2 id="auth-title">Entre no control plane.</h2>
            <p id="auth-copy">A base é profissional. O acesso também precisa ser.</p>
          </div>
          <div id="auth-alert" class="alert" role="alert" hidden></div>
          <form id="login-form" class="form-stack">
            <label>Email<input name="email" type="email" autocomplete="email" placeholder="voce@empresa.com" required /></label>
            <label>Senha<input name="password" type="password" autocomplete="current-password" placeholder="Mínimo de 12 caracteres" required /></label>
            <button class="button button-primary" type="submit">Entrar no control plane <span>↗</span></button>
          </form>
          <form id="signup-form" class="form-stack" hidden>
            <label>Nome completo<input name="full_name" autocomplete="name" placeholder="Seu nome" required minlength="2" /></label>
            <label>Empresa<input name="company_name" autocomplete="organization" placeholder="Nome da empresa" required minlength="2" /></label>
            <label>WhatsApp <span class="optional">opcional</span><input name="phone" type="tel" autocomplete="tel" placeholder="+55 11 99999-9999" /></label>
            <label class="check-row"><input name="whatsapp_opt_in" type="checkbox" value="true" /><span>Aceito receber uma mensagem de boas-vindas pelo WhatsApp</span></label>
            <label>Email<input name="email" type="email" autocomplete="email" placeholder="voce@empresa.com" required /></label>
            <label>Senha forte<input name="password" type="password" autocomplete="new-password" placeholder="Mínimo de 12 caracteres" required minlength="12" /></label>
            <label>Slug da organização <span class="optional">opcional</span><input name="tenant_slug" placeholder="minha-empresa" pattern="[a-z0-9-]+" /></label>
            <button class="button button-primary" type="submit">Criar ambiente <span>↗</span></button>
          </form>
          <button id="toggle-auth" class="button button-ghost" type="button">Ainda não tenho acesso</button>
          <p class="legal-note">Tokens de provider nunca são exibidos no navegador. Para produção, use Meta Cloud API com credenciais server-side e webhook assinado.</p>
        </div>
      </div>
    </section>

    <section id="dashboard-view" class="dashboard-layout" hidden>
      <button id="mobile-nav-backdrop" class="mobile-nav-backdrop" type="button" aria-label="Fechar menu principal"></button>
      <aside id="main-sidebar" class="sidebar" aria-label="Navegação principal">
        <div class="sidebar-head">
          <div class="brand-lockup"><span class="brand-mark">M</span><span>MAGO BOT</span></div>
          <button id="sidebar-close" class="sidebar-close" type="button" aria-label="Fechar menu principal">×</button>
        </div>
        <div class="side-label">OPERAÇÃO</div>
        <nav class="side-nav" aria-label="Navegação principal">
          <button class="side-link active" data-section="overview">Visão geral</button>
          <button class="side-link" data-section="projects">Projetos & providers</button>
          <button class="side-link" data-section="conversations">Conversas</button>
          <button class="side-link" data-section="keys">API keys</button>
          <button class="side-link" data-section="webhooks">Webhooks</button>
          <button class="side-link" data-section="usage">Uso & quotas</button>
          <button class="side-link" data-section="owner-whatsapp" hidden>WhatsApp do dono</button>
        </nav>
        <div class="sidebar-footer"><span class="status-dot"></span><span>Control plane online</span></div>
      </aside>
      <div class="dashboard-main">
        <header class="topbar">
          <div class="topbar-title"><button id="mobile-menu-toggle" class="mobile-menu-toggle" type="button" aria-controls="main-sidebar" aria-expanded="false" aria-label="Abrir menu principal">☰</button><div><p class="eyebrow">MAGO BOT / OPERAÇÃO</p><h2 id="dashboard-title">Visão geral</h2></div></div>
          <div class="topbar-actions"><span id="user-chip" class="user-chip"></span><button id="logout-button" class="button button-ghost small">Sair</button></div>
        </header>
        <div id="dashboard-alert" class="alert" role="alert" hidden></div>
        <div id="dashboard-content"></div>
      </div>
    </section>
  </main>
  <script src="/assets/platform-diagnostics.js" defer></script>
  <script src="/assets/platform-app.js" defer></script>
</body>
</html>"""
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})
