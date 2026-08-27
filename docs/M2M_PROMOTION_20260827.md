# Promoção M2M de Canais e Webhooks — API Mago Bot

**Data:** 2026-08-27
**Produto:** API Mago Bot — Produto de API
**Repositório:** https://github.com/aryperdomo123456789-web/api-mago-bot
**Superfície cliente:** https://app.mago-bot.com
**Provider operacional:** Evolution como compatibilidade; Meta Cloud permanece adapter oficial separado.
**Commit de código/documentação:** `9bef590` — https://github.com/aryperdomo123456789-web/api-mago-bot/commit/9bef590

## Escopo promovido

A API passou a expor uma superfície máquina-a-máquina autenticada exclusivamente por `X-API-Key` para canais e subscriptions downstream. O projeto da chave resolve tenant/projeto e todas as consultas e mutações são filtradas por esse vínculo. Cookies da Console não são aceitos nas rotas M2M.

O ciclo de canais cobre listagem, criação, status, connect, QR, pairing quando suportado pelo flavor, reconnect e disconnect. As respostas usam UUIDs públicos e não devolvem token de instância, API key do provider, senha, secret ou artefato efêmero no bloco genérico de provider. QR e pairing aparecem somente nos endpoints explicitamente solicitados e são tratados como credenciais/artefatos de alta sensibilidade.

Subscriptions downstream aceitam endpoint HTTPS validado contra SSRF e os eventos canônicos `message.inbound`, `message.status`, `connection.updated` e `qrcode.updated`. O worker assina o corpo JSON com HMAC-SHA256 no header `X-Mago-Signature`, acrescentando IDs de evento e delivery para correlação e deduplicação. O secret da subscription é retornado somente na criação.

A taxonomia Meta/Evolution é normalizada no gateway sem alterar o provider original, preservando provider event ID, payload sanitizado, deduplicação e state machine já existentes.

## Segurança e compatibilidade

As novas rotas são customer-only: em `app.mago-bot.com` sem chave retornam `401`; em `evo-api.mago-bot.com` retornam `404`. O Manager Evolution continua privado e responde `404` externamente. O contrato público usa `APIKeyHeader` no OpenAPI e não registra cookie/session security nas operações M2M.

A idempotência usa `X-Idempotency-Key` e hash canônico por tenant, projeto e operação. Replay da mesma chave e payload devolve o resultado idempotente; alteração de payload com a mesma chave deve resultar em conflito. As mutações permanecem auditáveis e correlacionadas com Operations persistentes.

## Evidências de validação

| Gate | Resultado |
|---|---|
| Compileall da aplicação | PASS |
| Contrato M2M e paths OpenAPI | PASS; 165 paths |
| Security scheme API key only | PASS |
| Normalização de eventos | PASS |
| HMAC-SHA256 e correlation headers | PASS |
| Redaction de provider | PASS |
| Isolamento app/evo-api | PASS; 401/404 conforme superfície |
| Public matrix | PASS |
| Containers essenciais | PASS; app, workers e DB healthy |
| Redis/Evolution/DB provider | PASS; running/healthy, sem restart de dependências |
| Logs sanitizados | PASS; sem traceback, NameError ou NoReferencedTableError |

A validação local e pública não usou API key real, não conectou número, não chamou provider real e não enviou mensagem. O teste de entrega usa evento/delivery determinísticos e transportes controlados; a entrega HTTPS com um endpoint externo de cliente ainda precisa ser executada no piloto com uma subscription real.

## Operação e rollback

O backup de produção desta promoção está em `/var/backups/mago-platform/owner-wildcard-20260827T225125Z`. O banco não recebeu migration nova nesta camada; foram reutilizadas as tabelas de subscriptions e Evolution já existentes. O rollback seguro é de código/containers: restaurar os arquivos versionados do backup, reconstruir somente app/workers e manter os bancos e provider em execução. Não há rollback destrutivo de schema associado a esta promoção.

## Limites restantes

A camada M2M está pronta para integração controlada, mas a emissão/rotação dedicada de secret de subscription para clientes enterprise deve receber uma operação de rotate/revoke antes do SLA comercial. Pairing code depende do flavor Evolution e pode ser rejeitado com `unsupported_operation`. Cancelamento de Operation é cooperativo e não desfaz uma chamada externa já aceita pelo provider. O próximo gate operacional é executar um piloto com API key de laboratório, número opt-in, endpoint HTTPS controlado e uma única mensagem, registrando delivery, retry e dead-letter sem envolver contatos reais.
