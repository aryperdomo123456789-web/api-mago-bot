from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..surface_auth import require_operations_surface

router = APIRouter(tags=["operations-ui"])


@router.get("/ops", response_class=HTMLResponse)
def operations_ui(request: Request) -> HTMLResponse:
    require_operations_surface(request)
    html = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Mago Bot Operations Console" />
  <title>Mago Bot | Operations Console</title>
      <link rel="stylesheet" href="/assets/ops.css?v=20260826-2" />
</head>
<body>
  <main class="ops-shell">
    <section id="ops-auth" class="ops-auth" aria-labelledby="ops-title">
      <div class="ops-brand"><span class="ops-mark">M</span><span>MAGO BOT / OPS</span></div>
      <p class="eyebrow">RESTRICTED OPERATIONS</p>
      <h1 id="ops-title">Central operacional.</h1>
      <p class="muted">Tenants, providers, filas, consumo e auditoria em uma fronteira administrativa própria.</p>
      <div id="ops-login-alert" class="ops-alert" hidden></div>
      <form id="ops-login-form" class="ops-form">
        <label>Email<input name="email" type="email" autocomplete="username" required /></label>
        <label>Senha<input name="password" type="password" autocomplete="current-password" required /></label>
        <button type="submit" class="ops-button primary">Entrar na operação</button>
      </form>
      <p class="security-note">MFA/step-up é requisito do gate de produção. Segredos de provider nunca são exibidos nesta interface.</p>
    </section>
    <section id="ops-dashboard" class="ops-dashboard" hidden>
      <button id="ops-nav-backdrop" class="ops-nav-backdrop" type="button" aria-label="Fechar menu operacional"></button>
      <aside id="ops-sidebar" class="ops-sidebar" aria-label="Navegação operacional">
        <div class="ops-sidebar-head">
          <div class="ops-brand"><span class="ops-mark">M</span><span>MAGO BOT / OPS</span></div>
          <button id="ops-sidebar-close" class="ops-sidebar-close" type="button" aria-label="Fechar menu operacional">×</button>
        </div>
        <nav aria-label="Operações">
          <button class="ops-nav active" data-panel="overview">Overview</button>
          <button class="ops-nav" data-panel="owner">Proprietário</button>
          <button class="ops-nav" data-panel="users">Usuários</button>
          <button class="ops-nav" data-panel="customers">Clientes / Tenants</button>
          <button class="ops-nav" data-panel="projects">Projetos</button>
          <button class="ops-nav" data-panel="licenses">Licenças e API Keys</button>
          <button class="ops-nav" data-panel="plans">Planos e Trials</button>
          <button class="ops-nav" data-panel="partners">Parceiros</button>
          <button class="ops-nav" data-panel="whatsapp">WhatsApp / Meta Cloud</button>
          <button class="ops-nav" data-panel="evolution">Evolution API</button>
          <button class="ops-nav" data-panel="stats">Estatísticas</button>
          <button class="ops-nav" data-panel="usage">Uso e quotas</button>
          <button class="ops-nav" data-panel="queues">Filas e falhas</button>
          <button class="ops-nav" data-panel="alerts">Alertas</button>
          <button class="ops-nav" data-panel="audit">Auditoria</button>
        </nav>
        <div class="ops-sidebar-footer"><span class="status-dot"></span> Console protegido</div>
      </aside>
      <div class="ops-main">
        <header class="ops-topbar"><div class="ops-topbar-title"><button id="ops-menu-toggle" class="ops-menu-toggle" type="button" aria-controls="ops-sidebar" aria-expanded="false" aria-label="Abrir menu operacional">☰</button><div><p class="eyebrow">MAGO BOT / OPERATIONS</p><h2 id="ops-panel-title">Overview</h2></div></div><div class="ops-topbar-actions"><button id="ops-logout" class="ops-button ghost">Sair</button></div></header>
        <div id="ops-alert" class="ops-alert" hidden></div>
        <div id="ops-content" class="ops-content"></div>
      </div>
    </section>
  </main>
    <script src="/assets/ops-app.js?v=20260826-2" defer></script>
</body>
</html>"""
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})
