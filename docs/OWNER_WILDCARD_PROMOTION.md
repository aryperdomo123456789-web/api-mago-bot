# Owner Wildcard e prontidão de produto — Registro de promoção

**Data:** 26 de agosto de 2026
**Branch:** `feat/operations-console-admin-migration`
**Commit publicado:** `db1c3795953a8983815a8a9466d4d2c98360284b`
**Repositório:** `aryperdomo123456789-web/appapiwppmago`

## Escopo entregue

A conta `owner` passou a operar como wildcard administrativo sobre tenants ativos na fachada customer-scoped, sem receber um bypass anônimo. O contrato usa a mesma sessão revogável, o enforcement de hostname e o RBAC existente. O owner pode usar a experiência customer-scoped e, adicionalmente, acessar operações de plataforma.

Foi implementado o endpoint `POST /v1/ops/owner/tenant-projects`, exclusivo para `owner`, que provisiona Tenant, membership `tenant_owner`, Subscription trial, PlatformProject e fila inicial opcional em uma transação auditada. Slugs e provider são validados por schema estrito; não é possível escolher papel arbitrário ou injetar campos extras.

O endpoint exige MFA habilitado e retorna `428 Precondition Required` quando o enrollment ainda está pendente. A Operations Console ganhou painel de setup/confirm de MFA, formulário de provisionamento owner-only e separação visual do projeto de licença legado.

A fachada customer-scoped reconhece owner como wildcard; usuários tenant continuam limitados ao membership. `app.mago-bot.com` aceita owner apenas para recursos customer-scoped, enquanto a Operations Console permanece em `evo-api.mago-bot.com`. O Manager bruto continua bloqueado.

Também foi corrigido o 500 do Overview causado pela ausência opcional de `email_deliveries`: as métricas Resend agora degradam para zero somente quando a relação opcional não existe; erros de outras tabelas continuam explícitos. O alerta global da Console é limpo quando uma visão renderiza com sucesso.

## Verificações

| Gate | Resultado |
|---|---|
| `python3 -m compileall -q service/app` | PASS |
| `node --check service/app/assets/ops-app.js` | PASS |
| `git diff --check` | PASS |
| Canário isolado | PASS; app/workers/DB healthy |
| Canário `/health/ready` | HTTP 200 |
| Canário owner endpoint sem sessão | HTTP 401 |
| Canário cross-surface app/evo-api | PASS |
| Canário OpenAPI | Paths owner/customer presentes; zero campos secretos relevantes |
| Produção app/webhook/owner-welcome/evolution-health | Healthy |
| Produção platform DB/Evolution DB | Healthy |
| Produção Redis/Evolution API | Running; sem healthcheck Docker nativo |
| Production `/health/ready` | HTTP 200 |
| `evo-api /`, `/ops`, `/docs`, `/openapi.json` | HTTP 200 |
| `evo-api /manager` | HTTP 404 |
| `evo-api /v1/ops/evolution/onboarding` sem sessão | HTTP 401 |
| `evo-api owner/tenant-projects` POST sem sessão | HTTP 401 |
| `app /admin`, `/docs`, `/openapi.json` | HTTP 200 |
| `app /v1/organizations`, `/v1/channels` sem sessão | HTTP 401 |
| `app /v1/ops/owner/tenant-projects` | HTTP 404 |
| OpenAPI público | 5 paths obrigatórios; zero propriedades secretas em channels/inbox |
| Logs recentes sanitizados | Sem Traceback, NoReferencedTableError, ModuleNotFoundError ou boot failure |

## Migrations e backups

As migrations `0008_evolution_instances.sql`, `0009_provider_integrations.sql` e `0010_inbox_distribution.sql` foram aplicadas anteriormente ao PostgreSQL de plataforma, uma a uma, e suas tabelas foram confirmadas. O banco Evolution não foi migrado nesta promoção. A migration Resend `0007` não foi promovida e nenhuma chave Resend foi configurada.

Backups de promoção estão no host, sob `/var/backups/mago-platform`. O backup da correção final foi:

`/var/backups/mago-platform/owner-wildcard-20260826T233137Z`

O dump do banco de plataforma recebeu SHA-256 `861232aa08ff5862b969fdb7829e6e896fe6e722a251246ec7afdb18f6935f3e`. O pacote de código anterior recebeu SHA-256 `62af69784c123a7adccdc557fef01dbf33eb6ccce10517747e6cdd242b3b3258`. O Compose efetivo anterior e atual recebeu SHA-256 `7bf335684848f2588406e0532a83ba32a6d0cfec7c0c6b3a12e93050383854ac`.

Não foram copiados para o GitHub ou para este documento: `.env`, chaves SSH, tokens, QR, URI TOTP, recovery codes, dumps como anexos, logs brutos ou credenciais de provider.

## Gates ainda pendentes

O enrollment MFA do owner continua pendente e deve ser concluído pelo proprietário no Google Authenticator ou autenticador TOTP compatível. Sem MFA, o provisionamento do tenant/projeto do laboratório fica bloqueado intencionalmente.

Depois do MFA, o fluxo do laboratório deve usar uma organização/projeto criado pela Operations Console, um canal Evolution dedicado e QR/pairing iniciado pela UI. Ainda não houve neste ciclo conexão autenticada do número real, entrega de mensagem, webhook inbound, claim/assignment, resposta controlada ou teste de boas-vindas. Esses eventos não devem ser declarados como concluídos.

Também permanecem como próximos gates o teste de restore em ambiente isolado, a política de suporte/SLA, billing real, E2E com dois tenants e o fechamento do composer visual. O Mago Bot está pronto para pilotos controlados e para continuar a construção comercial, não para prometer equivalência oficial ou escala ilimitada.

## Rollback

Em caso de falha de código, restaurar o `code-before.tgz` e o Compose anterior do diretório de backup correspondente, reconstruir somente `licensing-app`, `webhook-worker`, `owner-welcome-worker` e `evolution-health-worker`, e aguardar healthchecks. Não remover migrations de forma destrutiva. Não reiniciar DB, Redis ou Evolution API como primeira reação.
