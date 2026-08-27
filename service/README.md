# API Mago Bot — Produto de API


Serviço FastAPI do **API Mago Bot**, um control plane multi-tenant para mensageria, canais, conversas, automação, webhooks e operação profissional. Este serviço não é o **Mago Bot CRM** do repositório `project-hello`.

## Posicionamento

O Mago Bot é a camada de produto e governança. **Meta Cloud** é o provider oficial da WhatsApp Business Platform quando configurado. **Evolution** é um provider de compatibilidade premium para pilotos e operações opt-in; não deve ser apresentado como API oficial da Meta.

## Superfícies

- `https://evo-api.mago-bot.com/ops`: Operations Console restrita para owner e papéis operacionais.
- `https://app.mago-bot.com/admin`: portal customer-scoped para organizações, projetos, canais, inbox e API keys.
- `https://app.mago-bot.com/docs`: documentação OpenAPI do produto de API.
- `https://mago-bot.com/owner/login`: owner do produto separado Mago Bot CRM; não pertence a este serviço.
- `https://mago-bot.com`: usuário do produto separado Mago Bot CRM; não pertence a este serviço.

## Contratos principais

- `POST /v1/platform/auth/signup`: cria usuário, organização, membership e trial.
- `POST /v1/platform/auth/login`: cria sessão opaca e revogável.
- `GET /v1/platform/tenants/me`: lista organizações do usuário.
- `GET/POST /v1/platform/projects`: lista e cria projetos no tenant permitido.
- `POST /v1/platform/projects/{id}/keys`: cria API key de projeto; o token aparece uma única vez.
- `GET /v1/platform/projects/{id}/keys`: lista apenas prefixo, estado e metadados.
- `GET/POST /v1/organizations`: fachada de organizações customer-scoped.
- `GET/POST /v1/channels`: lifecycle de canais conforme provider e membership.
- `GET/POST /v1/conversations`: conversa e identidade no tenant correto.
- `POST /v1/messages`: envio normalizado com `X-API-Key` e idempotência.
- `GET/POST /v1/onboarding`: checklist e primeiro valor.
- `GET/POST /v1/inbox`: filas, assignment, claim, snooze, resolve e timeline.
- `/v1/webhooks/*`: eventos assinados, deduplicados e auditáveis.
- `/health/live` e `/health/ready`: liveness e readiness operacional.

## Headers de integração

Mutations devem enviar `X-Idempotency-Key` com pelo menos 16 caracteres. `X-Request-Id` pode ser fornecido pelo integrador e é propagado para rastreabilidade; quando ausente, a API gera um identificador. API keys devem ser enviadas em `X-API-Key` e nunca em query string, URL, frontend público ou log.

```bash
curl -X POST https://app.mago-bot.com/v1/projects/{project_id}/messages \\
  -H "X-API-Key: mb_live_REDACTED" \\
  -H "X-Idempotency-Key: pedido-0001" \\
  -H "Content-Type: application/json" \\
  -d '{"to":"5511999999999","type":"text","text":{"body":"Olá da API Mago Bot."}}'
```

## Compatibilidade legada

As rotas `/v1/licenses*`, o antigo catálogo de licenças e a tela **API keys e licenças legadas** continuam disponíveis apenas para migração. Elas não devem ser confundidas com as credenciais customer/project-scoped do produto atual.

## Segurança

Sessões são server-side, opacas, revogáveis e protegidas por cookie seguro. API keys são armazenadas como hash e exibidas somente na criação. Segredos Meta/Evolution são server-side e cifrados. Cada operação resolve tenant e projeto no servidor. O Manager Evolution permanece privado e não faz parte do contrato público.

O owner wildcard possui poderes administrativos adicionais e é protegido por MFA Google Authenticator/TOTP. O cliente final percorre o portal customer-scoped e não recebe acesso à Operations Console.

## Estrutura

- `app/main.py`: aplicação FastAPI e metadata OpenAPI da API Mago Bot.
- `app/routes/platform_ui.py`: portal do usuário.
- `app/routes/ops_ui.py`: Operations Console do owner.
- `app/routes/product_facade.py`: fachada pública do produto.
- `app/routes/onboarding.py`: onboarding e primeiro valor.
- `app/routes/channels_public.py`: canais customer-scoped.
- `app/routes/inbox.py`: inbox e distribuição.
- `app/providers/meta_cloud.py`: adapter oficial Meta Cloud.
- `app/providers/evolution.py`: adapter Evolution compatibilidade.
- `sql/migrations/`: schema versionado e transacional.

## Deploy

O runtime de produção fica em `/opt/mago-platform` e é servido pelo Docker Compose. O Nginx do aaPanel atua como proxy reverso para a aplicação; `/www/wwwroot/app.mago-bot.com` não é a origem do código privado.

O deploy deve seguir backup, canário, healthchecks, matriz de superfície, validação OpenAPI e rollback de código. Migrations são forward-only e não devem ser revertidas destrutivamente.
