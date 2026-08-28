# Recuperação da UI Canais — API Mago Bot

**Data:** 2026-08-28 UTC
**Produto:** API Mago Bot (`app.mago-bot.com`)
**Escopo:** Portal customer; CRM `project-hello` não foi alterado.

## Incidente observado

A sessão automatizada e a sessão Chrome do usuário eram ambientes separados. A sessão do sandbox expirou e o portal exibiu `session expired`, enquanto a sessão do usuário continuava autenticada. Em seguida, na tela Canais, o conteúdo aparecia, mas as interações pareciam inertes.

## Causa técnica identificada

A navegação aguardava o carregamento remoto da seção antes de renderizar o conteúdo, o que fazia a interface parecer congelada durante timeout ou falha de sessão. As ações de canal não tinham tratamento local de rejeição e não impediam cliques concorrentes. O wrapper de fetch também podia perder os headers padrão por causa da ordem de expansão das opções.

## Correção aplicada

O bundle customer passou a renderizar a seção imediatamente e carregar dados em segundo plano. As ações de conectar, reconectar, QR e status passaram a ter estado por canal/ação, feedback visual `Processando…`, bloqueio de duplicidade, captura de erro e alerta seguro. O wrapper de fetch preserva `Content-Type`, `X-Request-ID` e o timeout do interceptor. O `platform-app.js` recebeu novo cache-bust no HTML para impedir que o navegador reutilize o bundle antigo.

## Validação

- `node --check service/app/assets/platform-app.js`: PASS.
- `node --check service/app/assets/platform-diagnostics.js`: PASS.
- `python3 -m py_compile service/app/routes/platform_ui.py`: PASS.
- Canário isolado: health 200, autenticação, OpenAPI e log gate PASS.
- Produção: `health/ready=200`.
- Portal HTML: HTTP 200.
- Bundle com cache-bust novo: HTTP 200.
- Isolamento de `evo-api.mago-bot.com` para rota customer: HTTP 404.
- Log gate produtivo: PASS.
- Backup produtivo: `/var/backups/mago-platform/channels-ui-20260828T015153Z`.
- Container recriado: somente `licensing-app`.
- Não reiniciados: platform DB, Redis, Evolution API/DB/Redis, workers não relacionados, firewall e CRM.

## Versionamento

Commit seletivo: `0dd154f fix(portal): keep channel actions responsive`
Branch: `feat/operations-console-admin-migration`
Repositório: `aryperdomo123456789-web/api-mago-bot`

## Higiene de credenciais

A credencial M2M anterior foi tratada como comprometida e o usuário confirmou a rotação. Nenhum valor bruto de API key, token, QR, cookie, TOTP, segredo HMAC ou variável de provider foi armazenado neste relatório, no commit ou nos logs sanitizados.

## Limitação ainda pendente

A correção de UI não comprova a homologação E2E do número. Ainda faltam o QR novo, o scan no WhatsApp exclusivo de laboratório, o estado `connected`, o endpoint HTTPS controlado para subscription downstream, a validação HMAC/retry e qualquer mensagem opt-in controlada. Não declarar o E2E concluído antes desses gates.
