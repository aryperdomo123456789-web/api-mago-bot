# API Mago Bot — Produto de API

A **API Mago Bot** é um control plane multi-tenant para mensageria, automação, conversas e operação de canais. O produto normaliza autenticação, projetos, API keys, scopes, quotas, idempotência, webhooks, inbox, auditoria e observabilidade sem esconder as diferenças reais entre providers.

## Superfícies oficiais

| Superfície | URL | Responsabilidade |
|---|---|---|
| Operations Console / owner | https://evo-api.mago-bot.com | Administração, RBAC owner, provisionamento, MFA, providers e auditoria |
| Portal customer-scoped / usuário | https://app.mago-bot.com | Organização, projeto, onboarding, canais, inbox, API keys e webhooks |
| Documentação | https://app.mago-bot.com/docs | OpenAPI e referência pública do contrato |

## Providers

A **Meta Cloud** é o provider oficial da WhatsApp Business Platform quando configurado pelo cliente. A **Evolution** é um provider de compatibilidade premium para pilotos e operações opt-in; não é a API oficial da Meta. Os adapters, estados, credenciais, capabilities e mensagens de erro permanecem separados.

## O que já existe

A API possui autenticação por sessão revogável, RBAC, owner wildcard protegido por MFA, multi-tenancy, projetos públicos por UUID, API keys por projeto, scopes, quotas, idempotência, webhooks/outbox, retries, circuit breaker, auditoria append-only, healthchecks, tracing, onboarding, canais Evolution customer-scoped e inbox mínimo com filas e assignment.

## Quick start do cliente

O cliente cria ou recebe acesso a uma organização, escolhe um projeto, seleciona explicitamente Meta Cloud ou Evolution, configura o canal permitido pelo provider e usa uma API key de projeto com os scopes mínimos. Mutations devem enviar `X-Idempotency-Key`; requests podem usar `X-Request-Id` para rastreabilidade.

```bash
curl -X POST https://app.mago-bot.com/v1/projects/{project_id}/messages \\
  -H "X-API-Key: mb_live_REDACTED" \\
  -H "X-Idempotency-Key: pedido-0001" \\
  -H "Content-Type: application/json" \\
  -d '{
    "to": "5511999999999",
    "type": "text",
    "text": {"body": "Olá da API Mago Bot."}
  }'
```

O token exibido na criação da API key deve ser copiado pelo cliente diretamente na tela autenticada. Ele não deve ser enviado ao chat, versionado, colocado em frontend, URL ou log.

## Compatibilidade legada

As rotas de licenciamento continuam disponíveis para migração e clientes antigos, mas não representam o centro do produto. Elas devem ser tratadas como **Licensing Legacy**, sem confundir licença administrativa com API key customer/project-scoped.

A evolução do produto acontece nas fachadas `/v1/organizations`, `/v1/integrations`, `/v1/channels`, `/v1/conversations`, `/v1/messages`, `/v1/onboarding`, `/v1/inbox`, `/v1/jobs`, `/v1/webhooks`, `/v1/billing` e `/v1/analytics`, conforme o contrato de cada versão.

## Segurança e operação

O site público nunca chama a Evolution diretamente. O cliente fala com a API Mago Bot; o control plane resolve tenant, projeto, provider, capability, quota e credencial server-side. O Manager da Evolution permanece privado. Segredos de provider são cifrados em repouso e não são retornados por listagens ou OpenAPI.

Antes de produção comercial ampla, ainda devem ser concluídos e comprovados Embedded Signup Meta, billing real, SDKs, templates CRUD, mídia/interativos completos, rotação automatizada, status page, SLA e um E2E autenticado com número controlado. A Evolution deve ser vendida com posicionamento honesto de compatibilidade.

## Estrutura

- `service/app/main.py`: entrypoint FastAPI e metadata OpenAPI.
- `service/app/routes/platform_ui.py`: portal customer-scoped em `app.mago-bot.com`.
- `service/app/routes/ops_ui.py`: Operations Console em `evo-api.mago-bot.com`.
- `service/app/routes/product_facade.py`: fachada pública do produto.
- `service/app/routes/onboarding.py`: primeiro valor.
- `service/app/routes/channels_public.py`: canais Evolution customer-scoped.
- `service/app/routes/inbox.py`: filas, assignment e lifecycle de conversas.
- `service/app/providers/meta_cloud.py`: adapter Meta Cloud oficial.
- `service/app/providers/evolution.py`: adapter Evolution compatibilidade.
- `service/sql/migrations/`: migrations explícitas e transacionais.
- `docs/`: contratos, runbooks, prontidão e decisões de produto.

## Deploy

O runtime oficial usa Docker Compose no diretório privado `/opt/mago-platform`, com Nginx aaPanel como proxy reverso. O webroot `/www/wwwroot/app.mago-bot.com` não é a origem do código e deve permanecer sem aplicação estática privada.

Leia [`service/README_PLATFORM_V1.md`](service/README_PLATFORM_V1.md), [`docs/PRODUCT_GUIDE.md`](docs/PRODUCT_GUIDE.md) e [`docs/API_MAGO_BOT_IDENTITY.md`](docs/API_MAGO_BOT_IDENTITY.md) antes de operar o produto.
