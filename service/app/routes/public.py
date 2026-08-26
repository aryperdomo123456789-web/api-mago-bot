from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from ..core.config import Settings

router = APIRouter(tags=["public"])
settings = Settings()
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
BRAND_LOGO_PATH = ASSETS_DIR / "brand-logo-ui-20260805.png"
SHARE_CARD_PATH = ASSETS_DIR / "share-card-ui-20260805.png"

PUBLIC_APP_JS = """// Home pública enxuta: sem formulários pesados nem lógica extra."""

API_REFERENCE = {
    "service": "WhatsApp API Licensing",
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
    return Response(BRAND_LOGO_PATH.read_bytes(), media_type="image/png")


@router.get("/", response_class=HTMLResponse)
def public_home():
    html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>WhatsApp API Licensing | Mago Bot API</title>
  <meta name="description" content="Central de licenças para WhatsApp API com emissão, validação, revogação e documentação pronta para revenda e escala." />
  <meta name="theme-color" content="#07111f" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="WhatsApp API Licensing | Mago Bot API" />
  <meta property="og:description" content="Licenças com expiração, projetos separados e operação preparada para escalar uma WhatsApp API." />
  <meta property="og:url" content="https://licensing.mago-bot.com/" />
  <meta property="og:image" content="https://licensing.mago-bot.com/share-card.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="WhatsApp API Licensing | Mago Bot API" />
  <meta name="twitter:description" content="Licenças com expiração, projetos separados e operação preparada para escalar uma WhatsApp API." />
  <meta name="twitter:image" content="https://licensing.mago-bot.com/share-card.png" />
  <style>
    :root{
      --bg:#050816;
      --panel:#0b1220;
      --panel-2:#10182a;
      --line:rgba(255,255,255,.08);
      --text:#f5f8ff;
      --muted:#b0bdd1;
      --accent:#59d7ff;
      --accent-2:#7f8cff;
      --green:#8ef0a2;
      --shadow:0 24px 70px rgba(0,0,0,.36);
      --radius:24px;
      --max:1240px;
    }
    *{box-sizing:border-box}
    html{scroll-behavior:smooth}
    body{
      margin:0;
      color:var(--text);
      font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
      background:
        radial-gradient(circle at 15% 8%, rgba(89,215,255,.16), transparent 20%),
        radial-gradient(circle at 85% 0%, rgba(127,140,255,.12), transparent 26%),
        linear-gradient(180deg,#040712 0%, #07111f 52%, #050816 100%);
      min-height:100vh;
      overflow-x:hidden;
    }
    a{color:inherit;text-decoration:none}
    .container{max-width:var(--max); margin:0 auto; padding:0 22px}
    .nav{
      position:sticky;
      top:0;
      z-index:40;
      backdrop-filter:blur(16px);
      background:rgba(5,8,18,.84);
      border-bottom:1px solid rgba(255,255,255,.06);
    }
    .nav-inner{display:flex; align-items:center; justify-content:space-between; gap:18px; padding:16px 0}
    .brand{display:flex; align-items:center; gap:12px; font-weight:900; letter-spacing:.02em}
    .brand-mark{width:42px; height:42px; border-radius:14px; overflow:hidden; border:1px solid rgba(255,255,255,.08); background:#0d1525; flex:0 0 auto}
    .brand-mark svg{width:100%; height:100%; display:block}
    .nav-links{display:flex; align-items:center; gap:20px; color:var(--muted); font-size:.94rem; font-weight:700}
    .nav-links a:hover{color:var(--text)}
    .btn{
      display:inline-flex;
      align-items:center;
      justify-content:center;
      gap:10px;
      border-radius:999px;
      padding:13px 18px;
      font-weight:800;
      border:1px solid transparent;
      white-space:nowrap;
    }
    .btn-primary{background:linear-gradient(135deg,#8be7ff,#5dbdff 55%,#1560ff); color:#08111f; box-shadow:0 16px 34px rgba(93,189,255,.20)}
    .btn-secondary{background:rgba(255,255,255,.04); border-color:rgba(255,255,255,.08)}
    .hero{padding:46px 0 26px}
    .hero-grid{display:grid; grid-template-columns:1.02fr .98fr; gap:24px; align-items:center}
    .eyebrow{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:9px 14px;
      border-radius:999px;
      border:1px solid rgba(89,215,255,.20);
      background:rgba(89,215,255,.08);
      color:#ecfbff;
      font-size:.76rem;
      font-weight:900;
      letter-spacing:.14em;
      text-transform:uppercase
    }
    h1{margin:18px 0 12px; font-size:clamp(2.5rem,5.8vw,5.4rem); line-height:.95; letter-spacing:-.05em; max-width:11ch}
    .gradient{
      background:linear-gradient(90deg,#f7fbff 0%, #dfeaff 35%, #73d7ff 65%, #9a8cff 100%);
      -webkit-background-clip:text;
      background-clip:text;
      color:transparent
    }
    .hero-copy{margin:0; max-width:58ch; color:var(--muted); font-size:1.03rem; line-height:1.8}
    .bullets{display:grid; gap:10px; margin:22px 0 0; padding:0; list-style:none}
    .bullets li{display:flex; gap:10px; color:#dce6f8; line-height:1.55}
    .bullets li::before{content:"✓"; color:var(--green); font-weight:900}
    .hero-actions{display:flex; flex-wrap:wrap; gap:12px; margin-top:26px}
    .micro{display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px; margin-top:28px}
    .card{
      border:1px solid var(--line);
      border-radius:var(--radius);
      background:linear-gradient(180deg, rgba(11,17,31,.96), rgba(8,13,23,.98));
      box-shadow:var(--shadow)
    }
    .micro .card{padding:18px}
    .stat{font-size:1.55rem; font-weight:900; letter-spacing:-.04em}
    .stat-label{margin-top:6px; color:var(--muted); font-size:.92rem; line-height:1.5}
    .showcase{
      padding:22px;
      position:relative;
      overflow:hidden;
      min-height:640px;
      background:
        radial-gradient(circle at 12% 20%, rgba(89,215,255,.18), transparent 24%),
        radial-gradient(circle at 90% 10%, rgba(127,140,255,.12), transparent 26%),
        linear-gradient(180deg, rgba(10,16,28,.98), rgba(12,18,31,.98));
    }
    .showcase::before,.showcase::after{content:""; position:absolute; border-radius:999px; filter:blur(16px); opacity:.7}
    .showcase::before{width:240px; height:240px; right:-80px; top:24px; background:radial-gradient(circle, rgba(89,215,255,.18), transparent 70%)}
    .showcase::after{width:300px; height:300px; left:-120px; bottom:-120px; background:radial-gradient(circle, rgba(127,140,255,.18), transparent 70%)}
    .pill-row{display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; position:relative; z-index:1}
    .pill{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:9px 13px;
      border-radius:999px;
      background:rgba(255,255,255,.05);
      border:1px solid rgba(255,255,255,.08);
      color:#e5edf9;
      font-size:.88rem;
      font-weight:800
    }
    .dot{width:10px; height:10px; border-radius:50%; background:#56d9ff; box-shadow:0 0 0 6px rgba(86,217,255,.12)}
    .mock{
      margin-top:18px;
      padding:22px;
      border-radius:22px;
      border:1px solid rgba(255,255,255,.08);
      background:rgba(255,255,255,.03);
      position:relative;
      z-index:1
    }
    .mock h3{margin:0 0 10px; font-size:1.45rem}
    .mini-grid{display:grid; grid-template-columns:1fr 1fr; gap:14px}
    .mini-box{
      min-height:136px;
      padding:16px;
      border-radius:20px;
      border:1px solid rgba(255,255,255,.08);
      background:rgba(0,0,0,.18)
    }
    .mini-box strong{display:block; margin-bottom:8px; font-size:1rem}
    .mini-box p{margin:0; color:var(--muted); line-height:1.65}
    .code{
      margin-top:14px;
      border-radius:20px;
      overflow:hidden;
      border:1px solid rgba(255,255,255,.08);
      background:#08101d
    }
    .code-head{
      display:flex;
      justify-content:space-between;
      gap:10px;
      padding:12px 14px;
      border-bottom:1px solid rgba(255,255,255,.06);
      background:rgba(255,255,255,.03);
      color:#dfe8f7;
      font-size:.88rem;
      font-weight:800
    }
    pre{margin:0; padding:16px; color:#eef5ff; white-space:pre-wrap; word-break:break-word; line-height:1.7; font-size:.94rem}
    .section{padding:26px 0 8px}
    .head{display:flex; justify-content:space-between; align-items:end; gap:16px; margin-bottom:16px}
    .head h2{margin:0; font-size:clamp(1.7rem,2.8vw,2.8rem); letter-spacing:-.04em}
    .head p{margin:0; color:var(--muted); max-width:66ch; line-height:1.7}
    .grid-3,.grid-2{display:grid; gap:16px}
    .grid-3{grid-template-columns:repeat(3, minmax(0,1fr))}
    .grid-2{grid-template-columns:repeat(2, minmax(0,1fr))}
    .feature{padding:22px}
    .feature h3{margin:10px 0 8px; font-size:1.12rem}
    .feature p{margin:0; color:var(--muted); line-height:1.75}
    .icon{
      width:46px;
      height:46px;
      border-radius:16px;
      display:grid;
      place-items:center;
      font-weight:900;
      background:linear-gradient(135deg, rgba(89,215,255,.18), rgba(127,140,255,.16));
      border:1px solid rgba(255,255,255,.08)
    }
    .plans .card{padding:22px}
    .plan-price{font-size:2rem; font-weight:900; letter-spacing:-.05em; margin:16px 0 6px}
    .plan-price small{color:var(--muted); font-size:.9rem}
    .plan-list{display:grid; gap:10px; margin:16px 0 0; padding:0; list-style:none}
    .plan-list li{display:flex; gap:10px; color:#d9e4f6; line-height:1.5}
    .plan-list li::before{content:"✓"; color:var(--green); font-weight:900}
    .plan-card.highlight{border-color:rgba(89,215,255,.20); background:linear-gradient(180deg, rgba(12,20,38,.98), rgba(8,13,23,.98))}
    .badges{display:flex; flex-wrap:wrap; gap:10px; margin-top:16px}
    .badge{
      padding:8px 11px;
      border-radius:999px;
      background:rgba(255,255,255,.05);
      border:1px solid rgba(255,255,255,.07);
      color:#dfe6f5;
      font-size:.84rem;
      font-weight:800
    }
    .docs-box{padding:22px}
    .footer{padding:30px 0 42px; color:#8fa0b8; font-size:.92rem}
    .footer-bar{display:flex; justify-content:space-between; gap:16px; align-items:center; flex-wrap:wrap; border-top:1px solid rgba(255,255,255,.07); padding-top:18px}
    .footer-links{display:flex; flex-wrap:wrap; gap:16px}
    .footer-links a:hover{color:var(--text)}
    .section-anchor{scroll-margin-top:96px}
    @media (max-width:1100px){
      .hero-grid,.grid-3,.grid-2,.mini-grid{grid-template-columns:1fr}
      .nav-links{display:none}
      .showcase{min-height:auto}
      .head{flex-direction:column; align-items:flex-start}
      h1{max-width:100%}
      .micro{grid-template-columns:1fr}
    }
    @media (max-width:768px){
      .container{padding:0 16px}
      .nav-inner{padding:14px 0; flex-wrap:wrap}
      .nav .btn{flex:1 1 0}
      .hero{padding:28px 0 14px}
      h1{font-size:clamp(2.15rem,11vw,3.65rem)}
      .hero-copy{font-size:1rem; line-height:1.7}
      .hero-actions{flex-direction:column}
      .hero-actions .btn{width:100%}
      .showcase,.feature,.docs-box,.plans .card{padding:18px}
      .footer{padding-bottom:28px}
      .footer-bar{align-items:flex-start}
    }
    @media (max-width:520px){
      .brand{font-size:.98rem}
      .brand-mark{width:36px; height:36px; border-radius:12px}
      .pill{font-size:.8rem}
      .badge{font-size:.8rem}
      .plan-price{font-size:1.7rem}
      pre{font-size:.89rem}
    }
  </style>
</head>
<body>
  <header class="nav">
    <div class="container nav-inner">
      <a class="brand" href="#top" aria-label="Mago Bot API Home">
        <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 42 42" role="img" aria-label="Mago Bot"><defs><linearGradient id="mago-logo-gradient" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#67e8f9"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs><rect width="42" height="42" rx="14" fill="#0c1628"/><path d="M10 29V13h4.6l6.4 8.1 6.4-8.1H32v16h-4.2V19.7l-6.8 8.2h-.2l-6.7-8.2V29H10Z" fill="url(#mago-logo-gradient)"/><circle cx="34" cy="9" r="2" fill="#fbbf24"/></svg></span>
        <span>Mago Bot API</span>
      </a>
      <nav class="nav-links" aria-label="Navegação principal">
        <a href="#solucao">Solução</a>
        <a href="#planos">Planos</a>
        <a href="#partners">Partners</a>
        <a href="#docs">Docs</a>
      </nav>
      <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap">
        <a class="btn btn-secondary" href="/admin">Login</a>
        <a class="btn btn-primary" href="#planos">Gerar licença →</a>
      </div>
    </div>
  </header>

  <main id="top" class="container">
    <section class="hero section-anchor">
      <div class="hero-grid">
        <div>
          <span class="eyebrow">Licenças • WhatsApp API • Revenda</span>
          <h1><span class="gradient">Licenças</span> para uma WhatsApp API pronta para produto.</h1>
          <p class="hero-copy">Esta central gera, valida e revoga chaves de acesso para seu backend de WhatsApp, com scopes, projetos e auditoria para operar como SaaS.</p>
          <ul class="bullets">
            <li>Projetos separados por cliente, domínio e escopo.</li>
            <li>Chaves com expiração, status, revogação e auditoria.</li>
            <li>Fluxo pronto para conectar WhatsApp API e revender com controle.</li>
          </ul>
          <div class="hero-actions">
            <a class="btn btn-primary" href="#planos">Gerar licença →</a>
            <a class="btn btn-secondary" href="#docs">Ver documentação</a>
            <a class="btn btn-secondary" href="/v1/info">API status</a>
          </div>
          <div class="micro">
            <div class="card">
              <div class="stat">99.9%</div>
              <div class="stat-label">meta de disponibilidade para validação online</div>
            </div>
            <div class="card">
              <div class="stat">Multi-tenant</div>
              <div class="stat-label">cada cliente com conta, chave e projeto próprios</div>
            </div>
            <div class="card">
              <div class="stat">Scopes</div>
              <div class="stat-label">connect, send, webhook, read e write por licença</div>
            </div>
          </div>
        </div>

        <aside class="card showcase" aria-label="Preview do produto">
          <div class="pill-row">
            <span class="pill"><span class="dot"></span> Central de licenças</span>
            <span class="pill">WhatsApp API Licensing</span>
          </div>
          <div class="mock">
            <h3>Contrato de API</h3>
            <div class="mini-grid">
              <div class="mini-box">
                <strong>Emissão</strong>
                <p>Crie uma licença por cliente, projeto, domínio e escopo de uso.</p>
              </div>
              <div class="mini-box">
                <strong>Validação</strong>
                <p>Seu backend consulta a central antes de conectar, enviar ou receber eventos.</p>
              </div>
            </div>
            <div class="code">
              <div class="code-head"><span>Validação de licença</span><span>REST • JSON • assinatura</span></div>
              <pre>POST /v1/licenses/validate
{
  "token": "pd_live_xxx",
  "project_slug": "client-x",
  "scope": "whatsapp:connect",
  "domain": "app.client-x.com"
}</pre>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <section id="solucao" class="section section-anchor">
      <div class="head">
        <div>
          <h2>Como funciona</h2>
          <p>O fluxo é simples: você cria o projeto, gera a licença, valida no seu backend e revoga quando necessário.</p>
        </div>
      </div>
      <div class="grid-3">
        <article class="card feature">
          <div class="icon">1</div>
          <h3>Conta e projeto separados</h3>
          <p>Cada cliente recebe identidade, licença e escopo sem misturar acesso com outros projetos.</p>
        </article>
        <article class="card feature">
          <div class="icon">2</div>
          <h3>Chaves com controle real</h3>
          <p>Crie, limite, revise e revogue tokens com validade, status e rastreio de uso.</p>
        </article>
        <article class="card feature">
          <div class="icon">3</div>
          <h3>Pronto para escala</h3>
          <p>Estrutura pensada para parceiros, testes, produção e cobrança recorrente.</p>
        </article>
      </div>
    </section>

    <section id="planos" class="section section-anchor plans">
      <div class="head">
        <div>
          <h2>Planos de licença</h2>
          <p>Planos pensados para vender acesso à sua WhatsApp API com previsibilidade e limites claros.</p>
        </div>
      </div>
      <div class="grid-3">
        <article class="card plan-card">
          <span class="badge">Start</span>
          <h3>Start</h3>
          <p>Para testar o produto com uma operação enxuta.</p>
          <div class="plan-price">R$49,90 <small>/ mês</small></div>
          <ul class="plan-list">
            <li>1 projeto</li>
            <li>3 licenças ativas</li>
            <li>Scopes básicos</li>
          </ul>
          <a class="btn btn-secondary" href="/admin">Ativar no painel</a>
        </article>
        <article class="card plan-card highlight">
          <span class="badge">Pro</span>
          <h3>Pro</h3>
          <p>Para clientes que precisam de volume, organização e revenda.</p>
          <div class="plan-price">R$99,90 <small>/ mês</small></div>
          <ul class="plan-list">
            <li>Até 10 projetos</li>
            <li>Licenças com auditoria</li>
            <li>Validação e revogação</li>
          </ul>
          <a class="btn btn-primary" href="/admin">Gerar licença →</a>
        </article>
        <article class="card plan-card">
          <span class="badge">Elite</span>
          <h3>Elite</h3>
          <p>Operação sob contrato para parceiros e contas maiores.</p>
          <div class="plan-price">Sob consulta <small>/ SLA</small></div>
          <ul class="plan-list">
            <li>Quota personalizada</li>
            <li>Suporte avançado</li>
            <li>Domínio dedicado</li>
          </ul>
          <a class="btn btn-secondary" href="#partners">Quero ser partner</a>
        </article>
      </div>
      <div class="badges">
        <span class="badge">Licenças com expiração</span>
        <span class="badge">Revogação em tempo real</span>
        <span class="badge">Projeto por cliente</span>
        <span class="badge">Scopes por operação</span>
      </div>
    </section>

    <section id="partners" class="section section-anchor">
      <div class="head">
        <div>
          <h2>Programa Partner</h2>
          <p>Para quem quer revender, operar mais clientes e ter suporte prioritário com infraestrutura organizada.</p>
        </div>
      </div>
      <div class="grid-2">
        <article class="card feature">
          <div class="icon">P</div>
          <h3>Parceiro oficial</h3>
          <p>Melhor para quem quer revenda, onboarding assistido e limites personalizados por projeto.</p>
        </article>
        <article class="card feature">
          <div class="icon">S</div>
          <h3>Suporte e escala</h3>
          <p>Uma base pronta para crescer com mais contas, mais chaves e mais volume sem embolar a operação.</p>
        </article>
      </div>
    </section>

    <section id="docs" class="section section-anchor">
      <div class="head">
        <div>
          <h2>Docs rápidas</h2>
          <p>O essencial para o desenvolvedor começar sem adivinhar como integrar.</p>
        </div>
      </div>
      <div class="grid-2">
        <article class="card docs-box">
          <h3>Base URL</h3>
          <p><code>https://licensing.mago-bot.com</code></p>
          <h3>Auth</h3>
          <p>Sessão segura no portal <code>/platform</code>; chaves de API ficam restritas ao projeto.</p>
          <h3>Validação</h3>
          <p>O cliente envia a chave e o backend libera ou bloqueia o acesso.</p>
          <h3>Referência</h3>
          <p><code>/v1/reference</code> para o catálogo de rotas, scopes e fluxos.</p>
        </article>
        <article class="card docs-box">
          <h3>Emitir chave</h3>
          <div class="code">
            <div class="code-head"><span>POST /v1/keys</span><span>exemplo</span></div>
            <pre>curl -X POST https://licensing.mago-bot.com/v1/keys \
  -H "Content-Type: application/json" \
  -H "x-admin-token: SUA_CHAVE_ADMIN" \
  -d '{"label":"Cliente Elite","project_slug":"cliente-elite","scopes":["whatsapp:connect","whatsapp:send"]}'</pre>
          </div>
        </article>
      </div>
    </section>

    <footer class="footer">
      <div class="footer-bar">
        <div>
          <strong style="color:var(--text)">WhatsApp API Licensing</strong><br />
          <span>Central de licenças para vender acesso à sua WhatsApp API com projetos, scopes e revogação.</span>
        </div>
        <div class="footer-links">
          <a href="#solucao">Solução</a>
          <a href="#planos">Planos</a>
          <a href="#docs">Docs</a>
          <a href="/v1/info">API</a>
          <a href="/admin">Login</a>
        </div>
      </div>
    </footer>
  </main>
  <script src="/public-app.js" defer></script>
</body>
</html>
"""
    return HTMLResponse(
        html.replace("__APP_NAME__", settings.app_name)
        .replace("https://licensing.mago-bot.com", settings.public_base_url)
    )


@router.get("/v1/info")
def public_info():
    return {
        "service": settings.app_name,
        "product_name": "WhatsApp API Licensing",
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
            "name": "WhatsApp API Licensing",
            "positioning": "license platform for a WhatsApp API product",
        },
    }
