from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter(tags=["admin"])
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
ADMIN_APP_JS_PATH = ASSETS_DIR / "admin-app.js"


@router.get("/admin", response_class=HTMLResponse)
def admin_panel():
    html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>wp-api | Painel</title>
  <style>
    :root {
      --bg: #02040a;
      --panel: rgba(8, 13, 23, .94);
      --panel-2: rgba(12, 18, 31, .96);
      --line: rgba(149,177,212,.12);
      --text: #f8fbff;
      --muted: #b4c0d2;
      --primary: #59d7ff;
      --primary-2: #1560ff;
      --good: #71e7ff;
      --bad: #ff6b6b;
      --accent: #8b7bff;
      --navy: #0d1428;
      --navy-2: #060b15;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, Arial, sans-serif;
      color: var(--text);
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(89,215,255,.14), transparent 22%),
        radial-gradient(circle at top right, rgba(139,123,255,.12), transparent 26%),
        linear-gradient(180deg, #010208 0%, #07111f 45%, #02040a 100%);
      padding: 20px;
    }
    .wrap { width: min(100%, 1760px); margin: 0 auto; }
    .shell, .card, .hero, .tabbar {
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(10,15,26,.98), rgba(7,10,18,.98));
      border-radius: 24px;
      box-shadow: 0 24px 70px rgba(0,0,0,.34);
    }
    .hero { padding: 24px; margin-bottom: 18px; }
    .eyebrow {
      display:inline-flex; padding:8px 12px; border-radius:999px;
      background:rgba(89,215,255,.12); border:1px solid rgba(89,215,255,.22);
      color:#e6f8ff; font-size:.72rem; text-transform:uppercase; letter-spacing:.14em; font-weight:800;
    }
    h1 { margin: 14px 0 8px; font-size: clamp(2rem, 4vw, 3.4rem); line-height:1; }
    p { color: var(--muted); line-height: 1.6; }
    .login-wrap {
      width: 100%;
      max-width: 1720px;
      margin: 24px auto 0;
      padding: 0;
      overflow: hidden;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(420px, .92fr);
      min-height: calc(100vh - 48px);
      animation: fadeUp .45s ease both;
    }
    .login-copy {
      position: relative;
      padding: 40px 42px 44px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 24px;
      background:
        radial-gradient(circle at 16% 16%, rgba(89,215,255,.10), transparent 22%),
        radial-gradient(circle at 90% 12%, rgba(139,123,255,.10), transparent 22%),
        linear-gradient(135deg, var(--navy), var(--navy-2));
      border-right: 1px solid rgba(255,255,255,.06);
      animation: floatIn 1.2s ease both;
    }
    .login-copy::after {
      content: "";
      position: absolute;
      right: -120px;
      bottom: -120px;
      width: 300px;
      height: 300px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(89,215,255,.16), transparent 68%);
      filter: blur(10px);
      pointer-events: none;
    }
    .login-topline {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap: 12px;
      flex-wrap:wrap;
      z-index: 1;
    }
    .login-controls {
      display:flex;
      gap: 10px;
      flex-wrap:wrap;
      align-items:center;
    }
    .topchip {
      display:inline-flex;
      align-items:center;
      gap: 8px;
      height: 38px;
      padding: 0 14px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,.08);
      background: rgba(255,255,255,.05);
      color: #eef4ff;
      font-weight: 800;
      font-size: .88rem;
      letter-spacing: .02em;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
    }
    .topchip .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: linear-gradient(135deg, #8fe1ff, #59d7ff);
      box-shadow: 0 0 0 4px rgba(89,215,255,.12);
    }
    .login-brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-weight: 900;
      letter-spacing: .04em;
      text-transform: uppercase;
      color: #eef3ff;
    }
    .login-brand .mark {
      width: 54px;
      height: 54px;
      border-radius: 18px;
      overflow: hidden;
      background: radial-gradient(circle at 35% 30%, rgba(128,235,255,.32), rgba(83,107,255,.12));
      display: grid;
      place-items: center;
      border: 1px solid rgba(255,255,255,.10);
      box-shadow: 0 14px 34px rgba(93,189,255,.18);
    }
    .login-brand .mark img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      padding: 4px;
      display: block;
    }
    .login-copy h2 {
      margin: 12px 0 10px;
      font-size: clamp(2.2rem, 4vw, 4rem);
      line-height: .96;
      letter-spacing: -.05em;
      max-width: 12ch;
    }
    .login-copy p { max-width: 42ch; font-size: 1rem; }
    .login-form {
      padding: 40px 38px 38px;
      display:flex;
      flex-direction: column;
      justify-content:flex-start;
      align-items:center;
      gap: 18px;
      background:
        radial-gradient(circle at top right, rgba(93,189,255,.10), transparent 18%),
        linear-gradient(180deg, rgba(14,18,26,.98), rgba(9,12,18,.98));
      animation: floatIn 1.35s ease both;
    }
    .login-form h2 { font-size: 2rem; margin: 0 0 8px; }
    .login-form p { margin-top: 0; max-width: 40ch; }
    .login-form input {
      height: 54px;
      border-radius: 16px;
      background: rgba(255,255,255,.04);
    }
    .login-form form { display: grid; gap: 12px; }
    .login-form button {
      height: 54px;
      border-radius: 16px;
      color: #08101a;
    }
    .login-form button:disabled {
      opacity: .7;
      cursor: wait;
    }
    .login-links {
      display:flex;
      gap: 16px;
      flex-wrap: wrap;
      color: #cdd7ea;
      font-size: .92rem;
      font-weight: 700;
    }
    .login-links a { opacity: .85; }
    .login-links a:hover { opacity: 1; }
    .login-visual {
      display: grid;
      gap: 18px;
      align-content: start;
      padding: 34px 30px 30px;
      background:
        radial-gradient(circle at 50% 10%, rgba(103,225,255,.10), transparent 24%),
        linear-gradient(180deg, rgba(7,10,18,.95), rgba(7,10,18,.98));
    }
    .login-visual-head {
      font-size: .92rem;
      font-weight: 900;
      letter-spacing: .16em;
      text-transform: uppercase;
      color: #dbeaff;
    }
    .login-art {
      border-radius: 28px;
      padding: 18px;
      background:
        radial-gradient(circle at 30% 15%, rgba(93,189,255,.14), transparent 26%),
        linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.03));
      border: 1px solid rgba(255,255,255,.08);
      box-shadow: 0 30px 80px rgba(0,0,0,.34);
      display: grid;
      place-items: center;
      width: 100%;
      max-width: 620px;
      overflow: hidden;
    }
    .login-art img {
      width: 100%;
      height: auto;
      object-fit: contain;
      border-radius: 24px;
      box-shadow: 0 22px 50px rgba(0,0,0,.42);
      display: block;
    }
    .login-note {
      padding: 16px 18px;
      border-radius: 18px;
      background: rgba(255,255,255,.035);
      border: 1px solid rgba(255,255,255,.06);
      color: var(--muted);
      line-height: 1.5;
      width: 100%;
      max-width: 620px;
    }
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes floatIn {
      from { opacity: 0; transform: translateY(14px) scale(.99); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .grid { display:grid; grid-template-columns: 360px minmax(0,1fr); gap: 16px; align-items:start; }
    .grid-main { display:grid; gap: 16px; }
    .card { padding: 18px; }
    .tabbar { display:flex; flex-wrap:wrap; gap: 10px; padding: 10px; margin-bottom: 16px; }
    .tabbtn {
      border: 1px solid rgba(255,255,255,.08);
      background: rgba(255,255,255,.04);
      color: var(--text);
      padding: 12px 16px;
      border-radius: 999px;
      cursor:pointer;
      font-weight:800;
    }
    .tabbtn.active { background: linear-gradient(135deg, var(--primary), var(--primary-2)); }
    .tab { display:none; }
    .tab.active { display:block; }
    .row { display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .row3 { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .row4 { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    input, textarea, select, button {
      width: 100%;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,.08);
      background: rgba(255,255,255,.04);
      color: var(--text);
      padding: 12px 14px;
      outline: none;
    }
    textarea { min-height: 92px; resize: vertical; }
    button {
      cursor:pointer;
      background: linear-gradient(135deg, var(--primary), var(--primary-2));
      font-weight: 800;
    }
    button.secondary { background: rgba(255,255,255,.05); }
    button.danger { background: linear-gradient(135deg, #ff7b7b, #da3b5d); }
    .muted { color: var(--muted); font-size: .92rem; }
    .pill {
      display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px;
      background:rgba(49,213,138,.1); border:1px solid rgba(49,213,138,.16); color:#d8ffef; font-size:.78rem; font-weight:700;
    }
    .dangerpill { background: rgba(255,107,107,.12); border-color: rgba(255,107,107,.18); color:#ffe3e3; }
    .table { display:grid; gap: 10px; }
    .item {
      border: 1px solid rgba(255,255,255,.08); border-radius: 18px; padding: 14px; background: rgba(255,255,255,.03);
      display:flex; justify-content:space-between; gap:12px; align-items:flex-start; flex-wrap:wrap;
    }
    .item strong { display:block; margin-bottom:4px; }
    .item .meta { color: var(--muted); font-size: .88rem; line-height: 1.45; }
    .actions { display:flex; gap:8px; flex-wrap:wrap; }
    .actions button { width:auto; min-width: 110px; padding: 10px 14px; }
    .stats { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 10px; margin-top: 12px; }
    .stat {
      padding: 16px; border-radius: 18px; background: rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.06);
    }
    .stat b { display:block; font-size: 1.8rem; margin-top: 6px; }
    pre { white-space: pre-wrap; word-break: break-word; background: rgba(0,0,0,.24); border:1px solid rgba(255,255,255,.08); border-radius:16px; padding:12px; }
    .topbar { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
    .hidden { display:none !important; }
    @media (max-width: 1100px) {
      .grid, .row, .row3, .row4, .stats, .login-wrap { grid-template-columns: 1fr; }
      .login-copy { padding: 24px 22px 26px; border-right: none; border-bottom: 1px solid rgba(255,255,255,.06); }
      .login-form { padding: 28px; }
      .login-wrap { min-height: auto; }
      .login-art { min-height: 0; padding: 14px; }
      .login-art img { width: 100%; max-width: 520px; }
      .login-controls { width: 100%; }
      .topchip { height: 36px; }
    }
    @media (max-width: 768px) {
      body { padding: 12px; }
      .wrap { width: 100%; }
      .shell, .card, .hero, .tabbar, .login-wrap { border-radius: 18px; }
      .hero { padding: 18px; margin-bottom: 14px; }
      .hero h1 { font-size: clamp(1.8rem, 8vw, 2.6rem); }
      .login-wrap { margin-top: 14px; min-height: auto; }
      .login-copy,
      .login-form { padding: 22px; }
      .login-topline { flex-direction: column; align-items: flex-start; }
      .login-controls { gap: 8px; width: 100%; }
      .login-links { gap: 10px 14px; overflow-x: auto; width: 100%; padding-bottom: 2px; -webkit-overflow-scrolling: touch; }
      .login-mini { gap: 8px; }
      .stats { margin-top: 10px; }
      .tabbar {
        flex-wrap: nowrap;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        padding: 8px;
        gap: 8px;
      }
      .tabbtn {
        flex: 0 0 auto;
        white-space: nowrap;
      }
      .grid, .row, .row3, .row4, .stats { grid-template-columns: 1fr; }
      .card { padding: 16px; }
      .actions {
        flex-direction: column;
        align-items: stretch;
      }
      .actions button {
        width: 100%;
        min-width: 0;
      }
      input, textarea, select, button { min-width: 0; }
      .item {
        flex-direction: column;
      }
      .item .actions {
        width: 100%;
      }
      .topbar {
        align-items: flex-start;
      }
      .topbar .actions {
        width: 100%;
      }
    }
    @media (min-width: 1400px) {
      .login-copy { padding: 54px 52px 56px; }
      .login-form { padding: 56px; }
      .login-copy h2 { font-size: clamp(3rem, 3.8vw, 5rem); }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section id="dashboardShell" class="hidden">
    <section class="hero">
      <div class="topbar">
        <div>
          <div class="eyebrow">wp-api • Painel</div>
          <h1>Conta, usuários e licenças num lugar só</h1>
          <p>Faça login para gerenciar conta, usuários e licenças sem misturar com as chaves da API.</p>
        </div>
        <div class="actions">
          <button class="secondary" onclick="logout()">Sair</button>
        </div>
      </div>
      <div class="stats" id="stats">
        <div class="stat"><span class="muted">Sessão</span><b id="statSession">-</b></div>
        <div class="stat"><span class="muted">Conta</span><b id="statOwner">-</b></div>
        <div class="stat"><span class="muted">Usuários</span><b id="statUsers">-</b></div>
      </div>
    </section>
    </section>

    <section id="loginView" class="login-wrap card">
      <div class="login-copy">
        <div>
          <div class="login-topline">
            <div class="login-controls">
              <span class="topchip"><span class="dot"></span> PT-BR</span>
              <span class="topchip">Dark</span>
            </div>
            <span class="eyebrow" style="margin:0; background:rgba(89,215,255,.08); border-color:rgba(89,215,255,.16); color:#e7f8ff;">Acesso seguro</span>
          </div>
        <div style="margin-top: 20px;" class="login-brand">
            <span class="mark"><img src="/brand-logo-ui.png" alt="wp-api" loading="eager" decoding="async" /></span> wp-api
          </div>
          <h2>Entre na sua conta</h2>
          <p>Entre com seu e-mail e senha para continuar.</p>
        </div>
        <div style="margin-top: 18px; max-width: 620px;">
          <form id="loginForm">
            <div class="row">
              <div>
                <label class="muted">E-mail</label>
                <input id="loginEmail" value="mago@dono.pd" autocomplete="username" />
              </div>
              <div>
                <label class="muted">Senha</label>
                <input id="loginPassword" type="password" value="12345678" autocomplete="current-password" />
              </div>
            </div>
            <div class="actions" style="margin-top:12px;">
              <button id="loginSubmit" type="submit">Entrar</button>
              <button class="secondary" type="button" onclick="document.getElementById('loginPassword').value=''">Limpar</button>
            </div>
            <pre id="loginMsg" class="muted"></pre>
          </form>
          <div style="margin-top: 12px;">
            <button class="secondary" type="button" onclick="window.location.href='/'">Criar conta grátis</button>
          </div>
        </div>
      </div>
      <div class="login-form">
        <div class="eyebrow" style="margin-bottom:12px; background:rgba(89,215,255,.10); border-color:rgba(89,215,255,.18); color:#e7f8ff;">Crie sua conta</div>
        <div class="login-art" style="margin-top: 14px;">
          <img src="/share-card-ui.png" alt="wp-api visual" loading="eager" decoding="async" />
        </div>
        <div class="login-note">
          Crie sua conta grátis ou entre para continuar.
        </div>
      </div>
    </section>

    <section id="appView" class="hidden">
      <div class="tabbar">
        <button class="tabbtn active" data-tab="dashboard" onclick="showTab('dashboard')">Dashboard</button>
        <button class="tabbtn" data-tab="account" onclick="showTab('account')">Conta</button>
        <button class="tabbtn" data-tab="users" onclick="showTab('users')">Usuários</button>
        <button class="tabbtn" data-tab="licenses" onclick="showTab('licenses')">Licenças</button>
      </div>

      <div id="dashboard" class="tab active">
        <div class="grid-main">
          <section class="card">
            <h2>Resumo</h2>
            <p>Visão rápida da operação do dono e da central.</p>
            <div class="stats">
              <div class="stat"><span class="muted">Projetos</span><b id="dashProjects">-</b></div>
              <div class="stat"><span class="muted">Licenças</span><b id="dashLicenses">-</b></div>
              <div class="stat"><span class="muted">Assinantes</span><b id="dashSubscribers">-</b></div>
            </div>
          </section>
        </div>
      </div>

      <div id="account" class="tab">
        <div class="grid">
          <section class="card">
            <h2>Conta principal</h2>
            <p>Edite os dados principais da conta.</p>
            <div class="row">
              <div><label class="muted">Nome de exibição</label><input id="accDisplayName" /></div>
              <div><label class="muted">Empresa</label><input id="accCompanyName" /></div>
            </div>
            <div class="row">
              <div><label class="muted">E-mail</label><input id="accEmail" /></div>
              <div><label class="muted">Telefone</label><input id="accPhone" /></div>
            </div>
            <div>
              <label class="muted">Bio</label>
              <textarea id="accBio"></textarea>
            </div>
            <button onclick="saveAccount()">Salvar conta</button>
            <pre id="accountMsg" class="muted"></pre>
          </section>
          <section class="card">
            <h2>Dados da sessão</h2>
            <div id="meBox" class="muted">Carregando...</div>
          </section>
        </div>
      </div>

      <div id="users" class="tab">
        <div class="grid">
          <section class="card">
            <h2 id="userFormTitle">Criar usuário comum</h2>
            <p>Esses usuários serão seus assinantes ou operadores do produto.</p>
            <input type="hidden" id="userId" />
            <div class="row">
              <div><label class="muted">E-mail</label><input id="userEmail" /></div>
              <div><label class="muted">Nome</label><input id="userName" /></div>
            </div>
            <div class="row">
              <div><label class="muted">Senha</label><input id="userPassword" type="password" /></div>
              <div><label class="muted">Perfil</label>
                <select id="userRole">
                  <option value="subscriber">Assinante</option>
                  <option value="operator">Operador</option>
                  <option value="support">Suporte</option>
                </select>
              </div>
            </div>
            <div>
              <label class="muted">Observações</label>
              <textarea id="userNotes"></textarea>
            </div>
            <div class="actions">
              <button onclick="saveUser()">Salvar usuário</button>
              <button class="secondary" onclick="resetUserForm()">Novo</button>
            </div>
            <pre id="userMsg" class="muted"></pre>
          </section>
          <section class="card">
            <div class="topbar">
              <h2>Usuários cadastrados</h2>
              <button class="secondary" onclick="loadUsers()">Recarregar</button>
            </div>
            <div id="usersList" class="table"></div>
          </section>
        </div>
      </div>

      <div id="licenses" class="tab">
        <div class="grid">
          <div class="grid-main">
            <section class="card">
              <h2>Criar projeto</h2>
              <div class="row">
                <input id="projName" placeholder="Nome do projeto" />
                <input id="projSlug" placeholder="Slug único" />
              </div>
              <div class="row">
                <input id="projDomain" placeholder="Domínio" />
                <input id="projDesc" placeholder="Descrição" />
              </div>
              <button onclick="createProject()">Salvar projeto</button>
              <pre id="projectMsg" class="muted"></pre>
            </section>
            <section class="card">
              <h2>Emitir chave</h2>
              <div class="row">
                <input id="licLabel" placeholder="Label da chave" />
                <input id="licProjectSlug" placeholder="Slug do projeto" />
              </div>
              <div class="row">
                <input id="licExpires" placeholder="Expira em (ISO 8601, opcional)" />
                <input id="licCreatedBy" placeholder="Criado por" />
              </div>
              <textarea id="licScopes" placeholder="Scopes separados por vírgula: whatsapp:connect,whatsapp:send"></textarea>
              <input id="licNotes" placeholder="Observações" />
              <button onclick="issueLicense()">Emitir chave</button>
              <pre id="issueResult" class="muted"></pre>
            </section>
            <section class="card">
              <h2>Validar chave</h2>
              <input id="validateToken" placeholder="Cole a chave aqui" />
              <div class="row">
                <input id="validateScope" placeholder="Scope opcional" />
                <input id="validateProject" placeholder="Projeto opcional" />
              </div>
              <input id="validateDomain" placeholder="Domínio opcional" />
              <button onclick="validateLicense()">Validar</button>
              <pre id="validateResult" class="muted"></pre>
            </section>
          </div>
          <div class="grid-main">
            <section class="card">
              <div class="topbar">
                <h2>Projetos</h2>
                <button class="secondary" onclick="loadLicensing()">Recarregar</button>
              </div>
              <div id="projects" class="table"></div>
            </section>
            <section class="card">
              <div class="topbar">
                <h2>Licenças</h2>
                <button class="secondary" onclick="loadLicensing()">Recarregar</button>
              </div>
              <div id="licensesList" class="table"></div>
            </section>
          </div>
        </div>
      </div>
    </section>
  </div>

<script src="/admin-app.js" defer></script>
</body>
</html>
"""
    return html


@router.get("/admin-app.js")
def admin_app_js():
    return Response(ADMIN_APP_JS_PATH.read_text(), media_type="application/javascript")
