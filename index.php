<?php
header('Content-Type: text/html; charset=UTF-8');
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Licensing Central | Mago Bot</title>
    <style>
        :root {
            --bg: #05070c;
            --panel: rgba(14, 18, 26, .94);
            --panel-2: rgba(19, 24, 34, .96);
            --line: rgba(255,255,255,.08);
            --text: #f4f7fb;
            --muted: #aeb9c8;
            --primary: #34a0ff;
            --primary-2: #1969d7;
            --success: #28d38a;
        }
        * { box-sizing: border-box; }
        html, body { margin: 0; min-height: 100%; background:
            radial-gradient(circle at top left, rgba(52,160,255,.12), transparent 25%),
            radial-gradient(circle at top right, rgba(40,211,138,.10), transparent 28%),
            linear-gradient(180deg, #03050a 0%, #070b12 45%, #03050a 100%);
            color: var(--text);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        body { padding: 32px 18px 48px; }
        .wrap { max-width: 1200px; margin: 0 auto; }
        .hero {
            border: 1px solid var(--line);
            background: linear-gradient(180deg, rgba(16,20,28,.98), rgba(10,13,19,.98));
            border-radius: 28px;
            padding: 28px;
            box-shadow: 0 28px 80px rgba(0,0,0,.38);
        }
        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 9px 14px;
            border-radius: 999px;
            border: 1px solid rgba(52,160,255,.25);
            background: rgba(52,160,255,.12);
            color: #d8ebff;
            text-transform: uppercase;
            letter-spacing: .14em;
            font-size: .74rem;
            font-weight: 800;
        }
        h1 {
            margin: 18px 0 8px;
            font-size: clamp(2rem, 4vw, 4rem);
            line-height: 1;
        }
        p.lead {
            margin: 0;
            max-width: 900px;
            color: var(--muted);
            line-height: 1.6;
            font-size: 1.02rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
            margin-top: 18px;
        }
        .card {
            border: 1px solid var(--line);
            border-radius: 22px;
            background: var(--panel-2);
            padding: 18px;
            min-height: 170px;
        }
        .card h2 {
            margin: 0 0 10px;
            font-size: 1.02rem;
        }
        .card ul {
            margin: 0;
            padding-left: 18px;
            color: var(--muted);
            line-height: 1.6;
        }
        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 18px;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 46px;
            padding: 0 18px;
            border-radius: 999px;
            text-decoration: none;
            border: 1px solid var(--line);
            color: var(--text);
            background: rgba(255,255,255,.04);
            font-weight: 700;
        }
        .btn.primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-2));
            border-color: rgba(255,255,255,.08);
        }
        .status {
            margin-top: 18px;
            padding: 16px 18px;
            border-radius: 18px;
            border: 1px solid rgba(40,211,138,.18);
            background: rgba(40,211,138,.08);
            color: #dbfff0;
            line-height: 1.55;
        }
        .mono {
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            color: #e6eef7;
        }
        @media (max-width: 920px) {
            .grid { grid-template-columns: 1fr; }
            body { padding: 18px 12px 32px; }
            .hero { padding: 20px; }
        }
    </style>
</head>
<body>
    <main class="wrap">
        <section class="hero">
            <div class="eyebrow">Licensing Central</div>
            <h1>Mago Bot License SaaS</h1>
            <p class="lead">
                Esta é a central separada para emissão, validação, expiração e revogação de chaves de acesso
                para projetos que consomem a Evolution API. O objetivo é escalar com múltiplos bots e múltiplos
                clientes sem misturar permissões, bancos ou domínios.
            </p>

            <div class="grid">
                <article class="card">
                    <h2>Funções principais</h2>
                    <ul>
                        <li>Emitir chaves com prazo de validade</li>
                        <li>Revogar acesso a qualquer momento</li>
                        <li>Identificar projeto, domínio e cliente</li>
                        <li>Auditar último uso e histórico</li>
                    </ul>
                </article>
                <article class="card">
                    <h2>Modelo de segurança</h2>
                    <ul>
                        <li>Chave assinada e/ou hash no banco</li>
                        <li>Scopes por recurso e por operação</li>
                        <li>Validação online com fallback curto</li>
                        <li>Logs de uso por IP e aplicação</li>
                    </ul>
                </article>
                <article class="card">
                    <h2>Uso esperado</h2>
                    <ul>
                        <li>MagoBot consulta a licença antes de conectar</li>
                        <li>Projetos diferentes usam chaves diferentes</li>
                        <li>Expiração e revogação bloqueiam uso</li>
                        <li>Escala para vários bots sem embolar</li>
                    </ul>
                </article>
            </div>

            <div class="actions">
                <a class="btn primary" href="/">Abrir painel</a>
                <a class="btn" href="mailto:admin@mago-bot.com">Contato administrativo</a>
            </div>

            <div class="status">
                Status esperado: <span class="mono">site reservado para licensing.mago-bot.com</span>.<br>
                Próximo passo recomendado: conectar este domínio a um backend com banco próprio e API de validação.
            </div>
        </section>
    </main>
</body>
</html>
