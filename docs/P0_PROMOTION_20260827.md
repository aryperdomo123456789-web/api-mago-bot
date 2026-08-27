# API Mago Bot — Promoção dos três P0

**Data:** 2026-08-27
**Escopo:** Operations persistentes, idempotência unificada e envelope de erro estruturado.
**Produto:** API Mago Bot — Produto de API.
**CRM separado:** `project-hello` não fez parte desta promoção.

## Entrega

A API agora persiste `platform_operations` por organização/projeto, com `queued`, `running`, `cancel_requested`, `succeeded`, `failed`, `cancelled`, `aborted` e `expired`. Cada Operation guarda metadata, resposta, erro sanitizado, tentativas, timestamps, heartbeat e expiração padrão de 30 dias. O recurso público usa UUIDs de organização/projeto; IDs internos não são retornados.

Foram adicionadas as rotas públicas `GET /v1/operations`, `GET /v1/operations/{operation_id}`, `DELETE /v1/operations/{operation_id}` e `POST /v1/operations/{operation_id}:cancel`. Elas exigem scopes `operations:read` ou `operations:write`, filtram tenant e projeto e pertencem somente à superfície customer `app.mago-bot.com`. O host `evo-api.mago-bot.com` retorna `404` para essas rotas.

O hash canônico de payload e a validação de `X-Idempotency-Key` agora são compartilhados. A unicidade de mensagens e registros passou a considerar tenant, projeto, operação/endpoint e chave. Repetição com o mesmo payload retorna replay; reutilização com payload diferente retorna `409` com razão `IDEMPOTENCY_KEY_REUSED`. A criação de Operation trata corridas de unique constraint como replay seguro.

O envelope de erro é aditivo: mantém `detail` legado e inclui `error.code`, `message`, `status`, `reason`, `domain`, `retryable`, `retry_after_seconds`, `request_id` e `details`. O middleware não retorna stack trace, credenciais ou payloads sensíveis. `Retry-After` é enviado quando há janela de repetição recomendada.

## Migration e backup

A migration `0011_operations.sql` foi aplicada de forma idempotente exclusivamente no PostgreSQL de plataforma. Ela adicionou `project_id` a `idempotency_records`, ajustou as unicidades de mensagens/registros e criou `platform_operations` com seus índices e constraints. Nenhum banco Evolution foi migrado.

| Ambiente | Evidência | Estado |
|---|---|---|
| Canário | `/var/backups/mago-platform-canary/p0-0011-20260827T220303Z` | backup + migration aplicados |
| Produção, migration | `/var/backups/mago-platform/p0-0011-20260827T221450Z` | backup + migration aplicados |
| Produção, código | `/var/backups/mago-platform/owner-wildcard-20260827T221536Z` | backup + rebuild seletivo |

Dumps e arquivos secretos permanecem somente no servidor com permissões restritas; nenhum foi versionado ou anexado ao repositório.

## Gates executados

| Gate | Resultado |
|---|---|
| Compileall/import dos módulos | PASS |
| Hash canônico e chave mínima/máxima | PASS |
| Estados terminal/non-terminal | PASS |
| UUID público e ausência de IDs internos | PASS |
| Envelope AIP-193, request_id e Retry-After | PASS |
| Ausência de traceback/password/token no erro | PASS |
| OpenAPI com 3 rotas de Operations | PASS; 155 paths |
| Operations em `app.mago-bot.com` sem sessão | 401 |
| Operations em `evo-api.mago-bot.com` | 404 |
| Manager em `evo-api.mago-bot.com/manager` | 404 |
| Readiness público | 200 |
| App e workers | healthy |
| Logs sanitizados | PASS |

A validação de canário também passou com health, superfície, OpenAPI e logs antes da produção. O build utilizou a bundle fechada; o CRM `project-hello` não foi tocado.

## Compatibilidade e limites

O `POST /v1/messages` síncrono continua existindo e agora retorna a Operation correspondente como campo adicional. A entrega ainda não transforma toda mensagem em fila assíncrona; isso deve ser o próximo passo quando houver executor persistente de envio. O endpoint de Operations está pronto para polling e reconciliação, mas não deve ser apresentado como prova de entrega de WhatsApp: os estados `sent`, `delivered`, `read` e `failed` continuam pertencendo à mensagem e aos webhooks do provider.

A promoção não conectou número real, não enviou mensagem real e não ativou welcome. Meta Cloud continua sendo o provider oficial separado; Evolution continua sendo compatibilidade premium. O próximo gate operacional é um E2E controlado com API key customer/project-scoped, número de laboratório, opt-in, webhook, inbox e uma resposta única.
