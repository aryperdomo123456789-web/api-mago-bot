<?php
header('Content-Type: text/html; charset=UTF-8');
?>
<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#07111f">
    <meta name="description" content="API Mago Bot: control plane multi-tenant para canais, licenças, webhooks, quotas e operação de mensageria.">
    <meta property="og:title" content="API Mago Bot | Infraestrutura de conversa">
    <meta property="og:description" content="Uma API própria para conectar canais, organizar tenants e operar mensageria com segurança e rastreabilidade.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://app.mago-bot.com/">
    <meta property="og:image" content="https://app.mago-bot.com/assets/share-card-ui.png">
    <link rel="icon" type="image/png" sizes="512x512" href="/assets/brand-logo-ui.png">
    <link rel="apple-touch-icon" href="/assets/brand-logo-ui.png">
    <title>API Mago Bot | Infraestrutura de conversa</title>
    <style>
        :root {
            --bg: #050b15;
            --bg-soft: #091526;
            --panel: rgba(14, 28, 48, .86);
            --panel-strong: #0e1c30;
            --line: rgba(155, 194, 234, .16);
            --text: #f6fbff;
            --muted: #aabbd0;
            --primary: #39d6ff;
            --primary-strong: #1495d1;
            --violet: #9a7cff;
            --green: #42e2a0;
            --max: 1180px;
        }
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body {
            margin: 0;
            color: var(--text);
            background:
                radial-gradient(circle at 12% 4%, rgba(57, 214, 255, .13), transparent 28rem),
                radial-gradient(circle at 88% 16%, rgba(154, 124, 255, .15), transparent 30rem),
                linear-gradient(180deg, #050b15 0%, #071322 48%, #040913 100%);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.5;
        }
        a { color: inherit; }
        .container { width: min(var(--max), calc(100% - 40px)); margin: 0 auto; }
        .site-nav {
            position: fixed;
            inset: 0 0 auto;
            z-index: 50;
            height: 78px;
            border-bottom: 1px solid rgba(155, 194, 234, .14);
            background: rgba(5, 11, 21, .84);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }
        .nav-inner { height: 100%; display: flex; align-items: center; justify-content: space-between; gap: 28px; }
        .brand { display: inline-flex; align-items: center; gap: 12px; text-decoration: none; min-width: max-content; }
        .brand img { width: 42px; height: 42px; border-radius: 14px; border: 1px solid rgba(57, 214, 255, .35); box-shadow: 0 0 24px rgba(57, 214, 255, .18); }
        .brand-copy { display: grid; gap: 0; }
        .brand-copy strong { font-size: .98rem; letter-spacing: -.02em; }
        .brand-copy span { color: var(--primary); font-size: .65rem; font-weight: 800; letter-spacing: .17em; text-transform: uppercase; }
        .nav-links { display: flex; align-items: center; gap: 25px; color: var(--muted); font-size: .85rem; font-weight: 700; }
        .nav-links a { text-decoration: none; transition: color .2s ease; }
        .nav-links a:hover { color: var(--text); }
        .nav-actions { display: flex; align-items: center; gap: 10px; }
        .button { display: inline-flex; align-items: center; justify-content: center; gap: 9px; min-height: 42px; padding: 0 17px; border: 1px solid var(--line); border-radius: 12px; text-decoration: none; font-size: .8rem; font-weight: 800; transition: transform .2s ease, border-color .2s ease, background .2s ease; }
        .button:hover { transform: translateY(-1px); border-color: rgba(57, 214, 255, .65); }
        .button.primary { color: #02111b; background: linear-gradient(135deg, #5de4ff, #16a9df); border-color: transparent; }
        .button.ghost { color: var(--text); background: rgba(255,255,255,.04); }
        .button.owner { color: #efeaff; background: rgba(154, 124, 255, .13); border-color: rgba(154, 124, 255, .35); }
        main { padding-top: 78px; }
        .hero { padding: 92px 0 72px; }
        .hero-grid { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(370px, .92fr); align-items: center; gap: 68px; }
        .eyebrow { display: inline-flex; align-items: center; gap: 9px; padding: 8px 12px; border: 1px solid rgba(57, 214, 255, .27); border-radius: 999px; color: #b7f4ff; background: rgba(57, 214, 255, .09); font-size: .68rem; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; }
        .eyebrow::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 14px var(--green); }
        h1 { max-width: 720px; margin: 22px 0 18px; font-size: clamp(2.8rem, 6vw, 5.7rem); letter-spacing: -.075em; line-height: .96; }
        h1 span { color: var(--primary); }
        .lead { max-width: 640px; margin: 0; color: var(--muted); font-size: clamp(1rem, 1.8vw, 1.16rem); line-height: 1.75; }
        .hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 30px; }
        .trust-line { display: flex; flex-wrap: wrap; gap: 17px; margin-top: 26px; color: #8298b1; font-size: .76rem; font-weight: 700; }
        .trust-line span { display: inline-flex; align-items: center; gap: 7px; }
        .trust-line span::before { content: "✓"; color: var(--green); font-weight: 900; }
        .console-card { position: relative; padding: 17px; border: 1px solid rgba(129, 183, 229, .23); border-radius: 28px; background: linear-gradient(145deg, rgba(18, 40, 67, .94), rgba(9, 19, 34, .94)); box-shadow: 0 30px 90px rgba(0,0,0,.35), 0 0 60px rgba(57,214,255,.08); }
        .console-card::after { content: ""; position: absolute; width: 180px; height: 180px; right: -52px; bottom: -55px; border-radius: 50%; background: rgba(154,124,255,.18); filter: blur(26px); pointer-events: none; }
        .console-top { display: flex; align-items: center; justify-content: space-between; padding: 3px 4px 15px; }
        .console-brand { display: flex; align-items: center; gap: 10px; }
        .console-brand img { width: 34px; height: 34px; border-radius: 11px; }
        .console-brand strong { display: block; font-size: .82rem; }
        .console-brand small { display: block; color: #7992ac; font-size: .66rem; }
        .health { padding: 6px 10px; border-radius: 999px; color: #b9ffe4; background: rgba(66,226,160,.1); font-size: .65rem; font-weight: 900; }
        .console-body { display: grid; grid-template-columns: .78fr 1.22fr; gap: 12px; }
        .console-list, .console-chat { padding: 12px; border: 1px solid rgba(155, 194, 234, .11); border-radius: 16px; background: rgba(2, 9, 18, .45); }
        .console-list h3, .console-chat h3 { margin: 0 0 10px; font-size: .76rem; }
        .console-list p { margin: 0; padding: 11px 9px; border-top: 1px solid rgba(155,194,234,.08); color: #bdcce0; font-size: .68rem; }
        .console-list p:first-of-type { border-top: 0; }
        .console-list b { display: block; color: var(--text); font-size: .72rem; }
        .console-chat { display: flex; min-height: 190px; flex-direction: column; }
        .chat-head { display: flex; justify-content: space-between; padding-bottom: 11px; border-bottom: 1px solid rgba(155,194,234,.08); font-size: .7rem; }
        .chat-head span { color: var(--green); }
        .bubble { max-width: 86%; margin-top: 15px; padding: 10px 12px; border-radius: 13px; color: #c7d6e8; background: #1b2b40; font-size: .68rem; }
        .bubble.out { align-self: flex-end; color: #02202b; background: linear-gradient(135deg, #5de4ff, #23b9e8); }
        .console-footer { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; margin-top: 12px; }
        .console-stat { padding: 12px 10px; border-radius: 13px; background: rgba(255,255,255,.04); text-align: center; }
        .console-stat b { display: block; font-size: 1.1rem; }
        .console-stat span { color: #7891aa; font-size: .6rem; }
        section { padding: 86px 0; }
        .section-head { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 28px; }
        .section-head h2 { max-width: 650px; margin: 10px 0 0; font-size: clamp(1.9rem, 3.5vw, 3.25rem); letter-spacing: -.055em; line-height: 1; }
        .section-head p { max-width: 450px; margin: 0; color: var(--muted); line-height: 1.65; }
        .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
        .feature { min-height: 230px; padding: 24px; border: 1px solid var(--line); border-radius: 22px; background: linear-gradient(180deg, rgba(17, 35, 58, .82), rgba(8, 18, 32, .74)); }
        .feature .number { color: var(--primary); font-size: .72rem; font-weight: 900; letter-spacing: .15em; }
        .feature h3 { margin: 38px 0 9px; font-size: 1.2rem; }
        .feature p { margin: 0; color: var(--muted); font-size: .9rem; line-height: 1.65; }
        .surface-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
        .surface { padding: 27px; border: 1px solid var(--line); border-radius: 24px; background: rgba(12, 28, 48, .72); }
        .surface.owner { border-color: rgba(154,124,255,.3); background: linear-gradient(145deg, rgba(35, 24, 66, .65), rgba(12, 22, 39, .78)); }
        .surface h3 { margin: 0; font-size: 1.25rem; }
        .surface p { min-height: 54px; color: var(--muted); }
        .surface code { display: block; margin: 18px 0; padding: 14px; overflow-x: auto; border: 1px solid rgba(155,194,234,.12); border-radius: 13px; color: #bceeff; background: rgba(0,0,0,.25); font: .74rem/1.65 ui-monospace, SFMono-Regular, Menlo, monospace; }
        .api-section { border-top: 1px solid rgba(155,194,234,.1); border-bottom: 1px solid rgba(155,194,234,.1); }
        .api-layout { display: grid; grid-template-columns: .8fr 1.2fr; gap: 25px; align-items: stretch; }
        .api-list { display: grid; gap: 10px; }
        .api-item { display: flex; gap: 14px; align-items: flex-start; padding: 15px; border: 1px solid var(--line); border-radius: 15px; background: rgba(255,255,255,.025); }
        .api-item b { display: block; margin-bottom: 3px; font-size: .88rem; }
        .api-item span { color: var(--muted); font-size: .78rem; }
        .api-dot { width: 9px; height: 9px; flex: 0 0 auto; margin-top: 5px; border-radius: 50%; background: var(--primary); box-shadow: 0 0 15px rgba(57,214,255,.7); }
        .code-window { padding: 20px; border: 1px solid rgba(155,194,234,.16); border-radius: 22px; background: #030912; box-shadow: inset 0 0 50px rgba(57,214,255,.035); }
        .code-window .dots { display: flex; gap: 6px; margin-bottom: 19px; }
        .code-window .dots i { width: 8px; height: 8px; border-radius: 50%; background: #ef6a80; }
        .code-window .dots i:nth-child(2) { background: #f7c969; }
        .code-window .dots i:nth-child(3) { background: #5cdda5; }
        pre { margin: 0; overflow-x: auto; color: #c5d8ec; font: .78rem/1.75 ui-monospace, SFMono-Regular, Menlo, monospace; }
        .code-key { color: #62dcff; }
        .code-string { color: #b6f09a; }
        .code-comment { color: #62758d; }
        .cta { padding: 45px; border: 1px solid rgba(57,214,255,.24); border-radius: 28px; background: radial-gradient(circle at 90% 20%, rgba(154,124,255,.21), transparent 25rem), linear-gradient(135deg, rgba(13, 52, 76, .95), rgba(10, 22, 39, .95)); }
        .cta h2 { max-width: 670px; margin: 0 0 11px; font-size: clamp(2rem, 4vw, 3.5rem); letter-spacing: -.06em; line-height: 1; }
        .cta p { max-width: 650px; margin: 0; color: #bed0e2; }
        footer { padding: 28px 0 45px; color: #7790aa; font-size: .78rem; }
        .footer-inner { display: flex; justify-content: space-between; gap: 22px; padding-top: 24px; border-top: 1px solid rgba(155,194,234,.11); }
        .footer-links { display: flex; flex-wrap: wrap; gap: 18px; }
        .footer-links a { color: #a9bfd4; text-decoration: none; }
        @media (max-width: 980px) {
            .nav-links { display: none; }
            .hero-grid, .api-layout { grid-template-columns: 1fr; }
            .hero { padding-top: 68px; }
            .console-card { max-width: 680px; }
        }
        @media (max-width: 680px) {
            .container { width: min(var(--max), calc(100% - 26px)); }
            .site-nav { height: 70px; }
            main { padding-top: 70px; }
            .brand-copy span { font-size: .55rem; }
            .nav-actions .owner { display: none; }
            .nav-actions .button { min-height: 38px; padding: 0 12px; font-size: .72rem; }
            .hero { padding: 52px 0 35px; }
            .hero-grid, .surface-grid, .feature-grid, .console-body { grid-template-columns: 1fr; }
            .console-chat { min-height: 155px; }
            section { padding: 60px 0; }
            .section-head { display: block; }
            .section-head p { margin-top: 15px; }
            .cta { padding: 27px 22px; }
            .footer-inner { display: block; }
            .footer-links { margin-top: 16px; }
        }
    </style>
</head>
<body>
    <header class="site-nav">
        <div class="container nav-inner">
            <a class="brand" href="#top" aria-label="API Mago Bot, início">
                <img src="/assets/brand-logo-ui.png" alt="Logo API Mago Bot">
                <span class="brand-copy"><strong>API Mago Bot</strong><span>produto de API</span></span>
            </a>
            <nav class="nav-links" aria-label="Navegação principal">
                <a href="#produto">Produto</a>
                <a href="#superficies">Superfícies</a>
                <a href="#api">API</a>
                <a href="#seguranca">Segurança</a>
            </nav>
            <div class="nav-actions">
                <a class="button ghost" href="https://app.mago-bot.com/admin">Portal usuário</a>
                <a class="button owner" href="https://evo-api.mago-bot.com/ops">Área owner</a>
            </div>
        </div>
    </header>

    <main id="top">
        <section class="hero">
            <div class="container hero-grid">
                <div>
                    <div class="eyebrow">API MAGO BOT / CONTROL PLANE</div>
                    <h1>Conecte a operação. <span>Controle a escala.</span></h1>
                    <p class="lead">Uma API própria para organizar tenants, canais, licenças, webhooks, quotas e eventos de mensageria em uma fronteira segura. Meta Cloud oficial ou Evolution como adapter: o seu produto fala com um contrato consistente.</p>
                    <div class="hero-actions">
                        <a class="button primary" href="https://app.mago-bot.com/admin">Entrar no portal <span>↗</span></a>
                        <a class="button ghost" href="/docs">Ver documentação da API <span>↗</span></a>
                    </div>
                    <div class="trust-line"><span>Multi-tenant</span><span>Webhooks assinados</span><span>OpenAPI</span></div>
                </div>
                <div class="console-card" aria-label="Prévia da operação da API Mago Bot">
                    <div class="console-top">
                        <div class="console-brand"><img src="/assets/brand-logo-ui.png" alt=""><div><strong>API Mago Bot</strong><small>control plane online</small></div></div>
                        <span class="health">● Operação saudável</span>
                    </div>
                    <div class="console-body">
                        <div class="console-list"><h3>Recursos</h3><p><b>Clientes / tenants</b>isolamento ativo</p><p><b>Canais</b>provider controlado</p><p><b>Webhooks</b>assinatura verificada</p><p><b>Quotas</b>consumo rastreável</p></div>
                        <div class="console-chat"><div class="chat-head"><b>Evento de conversa</b><span>processado</span></div><div class="bubble">message.received<br>provider_event_id: evt_••••</div><div class="bubble out">Roteado para fila Suporte<br>trace_id: req_••••</div></div>
                    </div>
                    <div class="console-footer"><div class="console-stat"><b>99,9%</b><span>disponibilidade alvo</span></div><div class="console-stat"><b>HMAC</b><span>webhook seguro</span></div><div class="console-stat"><b>v1</b><span>contrato versionado</span></div></div>
                </div>
            </div>
        </section>

        <section id="produto">
            <div class="container">
                <div class="section-head"><div><div class="eyebrow">O que existe aqui</div><h2>Infraestrutura para parar de remendar integração.</h2></div><p>A API Mago Bot não é o CRM. Ela é a camada de controle e orquestração que dá contratos, limites e rastreabilidade para produtos que consomem canais e automações.</p></div>
                <div class="feature-grid">
                    <article class="feature"><div class="number">01 / CONTROL PLANE</div><h3>Tenants e licenças</h3><p>Projetos, organizações, usuários, API keys, scopes, planos, trials e consumo separados por cliente.</p></article>
                    <article class="feature"><div class="number">02 / CHANNEL LAYER</div><h3>Canais desacoplados</h3><p>Um contrato interno para Evolution e Meta Cloud, com status, webhooks, retries e provider sem contaminar o produto consumidor.</p></article>
                    <article class="feature" id="seguranca"><div class="number">03 / TRUST LAYER</div><h3>Segurança rastreável</h3><p>Segredos server-side, HMAC, rate limit, circuit breaker, auditoria, quotas e diagnóstico por request.</p></article>
                </div>
            </div>
        </section>

        <section id="superficies">
            <div class="container">
                <div class="section-head"><div><div class="eyebrow">Duas superfícies, uma fronteira</div><h2>Cada usuário entra no lugar certo.</h2></div><p>Owner e usuário comum não dividem a mesma porta. Cada domínio tem uma função explícita, com autenticação e permissões próprias.</p></div>
                <div class="surface-grid">
                    <article class="surface owner"><div class="number">ÁREA OWNER / OPERATIONS</div><h3>evo-api.mago-bot.com</h3><p>Console restrito para governar plataforma, usuários, tenants, licenças, planos, providers, Evolution, Meta, filas e auditoria.</p><code>https://evo-api.mago-bot.com/ops</code><a class="button owner" href="https://evo-api.mago-bot.com/ops">Abrir console owner ↗</a></article>
                    <article class="surface"><div class="number">ÁREA USUÁRIO / PORTAL</div><h3>app.mago-bot.com</h3><p>Portal do cliente para criar ambiente, acompanhar projetos, canais, conversas, webhooks, API keys e consumo dentro do próprio tenant.</p><code>https://app.mago-bot.com/admin</code><a class="button primary" href="https://app.mago-bot.com/admin">Abrir portal usuário ↗</a></article>
                </div>
            </div>
        </section>

        <section id="api" class="api-section">
            <div class="container api-layout">
                <div><div class="eyebrow">Contrato versionado</div><h2>Uma API para o produto falar com todos os canais.</h2><p class="lead">O contrato público deve ser previsível: autenticação por escopo, paginação, idempotência, erros normalizados e eventos assíncronos. Nada de payload secreto no browser.</p><div class="api-list"><div class="api-item"><i class="api-dot"></i><div><b>Resources</b><span>Tenants, projetos, chaves e licenças.</span></div></div><div class="api-item"><i class="api-dot"></i><div><b>Messaging</b><span>Conversas, mensagens, mídia e status.</span></div></div><div class="api-item"><i class="api-dot"></i><div><b>Events</b><span>Webhooks, outbox, retries, DLQ e replay.</span></div></div></div></div>
                <div class="code-window"><div class="dots"><i></i><i></i><i></i></div><pre><span class="code-comment">// enviar uma mensagem com idempotência</span>
POST <span class="code-string">/v1/conversations/{id}/messages</span>
Authorization: Bearer &lt;api-key&gt;
Idempotency-Key: msg-unique-123

{
  <span class="code-key">"type"</span>: <span class="code-string">"text"</span>,
  <span class="code-key">"text"</span>: <span class="code-string">"Olá, operação."</span>,
  <span class="code-key">"channel_id"</span>: <span class="code-string">"ch_••••"</span>
}

<span class="code-comment">// retorno normalizado</span>
{ <span class="code-key">"message_id"</span>: <span class="code-string">"msg_••••"</span>, <span class="code-key">"status"</span>: <span class="code-string">"queued"</span> }</pre></div>
            </div>
        </section>

        <section>
            <div class="container"><div class="cta"><h2>A API não deve ser o gargalo do seu produto.</h2><p>Comece pelo portal, valide o contrato no Swagger e evolua do sandbox para o canário com observabilidade. O CRM Mago Bot consome essa camada; são produtos diferentes, com responsabilidades diferentes.</p><div class="hero-actions"><a class="button primary" href="https://app.mago-bot.com/docs">Abrir Swagger ↗</a><a class="button ghost" href="mailto:contato@app.mago-bot.com">Falar com a operação</a></div></div></div>
        </section>
    </main>

    <footer><div class="container footer-inner"><span>© 2026 API Mago Bot · Produto de API independente do Mago Bot CRM.</span><div class="footer-links"><a href="https://evo-api.mago-bot.com/ops">Owner</a><a href="https://app.mago-bot.com/admin">Usuário</a><a href="/docs">Documentação</a><a href="/health">Health</a></div></div></footer>
</body>
</html>

<!-- API Mago Bot: control plane e gateway de produto. O CRM vive no project-hello. -->
