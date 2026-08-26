# WhatsApp API Licensing

Central de licenças, chaves e auditoria para um produto de WhatsApp API.

## O que este serviço resolve

- emissão de chaves com expiração
- validação online de licença
- revogação imediata
- separação por projeto, domínio e scopes
- trilha de auditoria para alto volume
- base para distribuir acesso a uma WhatsApp API própria

## Rotas principais

- `GET /` página pública de produto e documentação
- `GET /v1/info` catálogo público da API
- `GET /v1/reference` referência estruturada com fluxos, endpoints e scopes
- `POST /v1/projects` cria projeto
- `GET /v1/projects` lista projetos
- `POST /v1/keys` emite chave
- `GET /v1/keys` lista chaves
- `GET /v1/keys/{id}` detalha chave
- `POST /v1/keys/validate` valida chave
- `POST /v1/keys/{id}/revoke` revoga chave

## Compatibilidade legada

As rotas antigas continuam ativas:

- `POST /v1/licenses/projects`
- `POST /v1/licenses`
- `POST /v1/licenses/validate`
- `GET /v1/licenses/projects`
- `GET /v1/licenses`
- `GET /v1/licenses/{id}`
- `POST /v1/licenses/{id}/revoke`

## Autenticação

Operações administrativas exigem o cabeçalho:

```bash
x-admin-token: SEU_TOKEN_ADMIN
```

Validação de licença não usa token administrativo. O cliente envia apenas a chave emitida.

## Formato da chave

A chave emitida retorna:

- `token` para o cliente salvar
- `license.uuid` como identificador público
- `license.status`
- `license.expires_at`
- `license.revoked_at`
- `license.scopes`

## Fluxo recomendado

1. Criar projeto com `slug` único.
2. Emitir uma chave para aquele projeto.
3. O cliente valida antes de iniciar o consumo da API.
4. Se a licença vencer ou for revogada, o cliente bloqueia o uso.
5. Auditoria fica registrada no banco.

## Scopes suportados

- `whatsapp:connect`
- `whatsapp:send`
- `whatsapp:webhook`
- `license:read`
- `license:write`

## Como a WhatsApp API usa a licença

O backend da sua WhatsApp API deve:

1. Receber a chave emitida pela central.
2. Validar `project_slug`, `domain` e `scope`.
3. Bloquear conexão, envio ou webhook se a licença falhar.
4. Revalidar em operações sensíveis e antes de renovar sessão.
5. Revogar o acesso quando a licença mudar de status.

## Exemplos

Emitir chave:

```bash
curl -X POST https://licensing.mago-bot.com/v1/keys \
  -H "Content-Type: application/json" \
  -H "x-admin-token: SEU_TOKEN_ADMIN" \
  -d '{
    "label": "Projeto X",
    "project_slug": "projeto-x",
    "scopes": ["whatsapp:connect", "whatsapp:send"],
    "created_by": "admin"
  }'
```

Validar chave:

```bash
curl -X POST https://licensing.mago-bot.com/v1/keys/validate \
  -H "Content-Type: application/json" \
  -d '{
    "token": "CHAVE_RECEBIDA",
    "project_slug": "projeto-x",
    "scope": "whatsapp:connect",
    "domain": "app.projeto-x.com"
  }'
```

Revogar chave:

```bash
curl -X POST https://licensing.mago-bot.com/v1/keys/123/revoke \
  -H "x-admin-token: SEU_TOKEN_ADMIN"
```

## Estrutura

- `app/main.py`: aplicação FastAPI
- `app/models.py`: modelo do banco
- `app/routes/public.py`: página pública, catálogo e referência
- `app/routes/product.py`: rotas limpas do produto
- `app/routes/licenses.py`: compatibilidade legada
- `app/routes/admin.py`: painel interno
- `app/routes/health.py`: health check
- `sql/schema.sql`: base relacional para PostgreSQL

## Deploy

Suba este serviço no aaPanel como Python Project apontando para a porta definida em `LICENSE_PORT`.
