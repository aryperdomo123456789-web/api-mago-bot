# Plano de deploy canário — Mago Bot Platform

## Princípio

A primeira versão do produto não substitui o container estável sem evidência. O canário roda em `127.0.0.1:4350`, compartilha apenas o banco/rede necessários e permanece sem publicação externa até passar pelos checks.

## Pré-condições

O operador deve gerar `PLATFORM_SESSION_SECRET`, `PLATFORM_SECRET_KEY`, `META_APP_SECRET`, `META_WEBHOOK_VERIFY_TOKEN`, `META_SYSTEM_USER_TOKEN` e `METRICS_TOKEN` fora do repositório. O backup PostgreSQL precisa estar comprovado por restauração em ambiente separado. A migração `0001_platform_foundation.sql` deve ser aplicada uma vez no banco de staging e depois no banco de produção durante janela aprovada. `PLATFORM_AUTO_CREATE_SCHEMA` permanece `false`.

## Sequência de staging

```bash
set -euo pipefail
cd /opt/mago-platform
cp service.env service.env.backup.$(date -u +%Y%m%dT%H%M%SZ)
docker compose -f docker-compose.production.yml build licensing-app webhook-worker
psql "$LICENSE_DATABASE_URL" -v ON_ERROR_STOP=1 -f service/sql/migrations/0001_platform_foundation.sql
docker compose -f docker-compose.production.yml -f docker-compose.canary.yml up -d licensing-app-canary
curl --fail http://127.0.0.1:4350/health/live
curl --fail http://127.0.0.1:4350/docs
curl --fail-with-body -i http://127.0.0.1:4350/v1/platform/auth/me | grep -q '401'
```

Em seguida, executar smoke de webhook com payload sintético assinado fora de produção, checar `X-Request-ID`, CSP, HSTS e o endpoint `/health/ready`. Não enviar mensagem real durante smoke sem autorização explícita e número de teste.

## Promoção

A promoção exige: health live e ready verdes; migrations registradas em `schema_migrations`; zero erro de import/build; worker `mago_webhook_worker` ativo; backup recente; logs sem tokens; uma mensagem de teste Meta com opt-in e template permitido; webhook recebido, deduplicado e entregue; e rollback testado.

Somente após os critérios passarem o operador direciona o proxy `app.mago-bot.com` para a nova instância. Evolution permanece atrás de sua própria superfície e não é misturada ao contrato Meta Cloud.

## Rollback

Se qualquer critério falhar, não aplicar segunda migração destrutiva. Retirar o upstream canário do proxy, parar apenas `licensing-app-canary`, preservar os dados criados nas tabelas novas e restaurar o serviço estável. A reversão de schema só ocorre por migração reversa revisada; não usar `DROP TABLE` como rollback de emergência. Como a base nova é aditiva, o serviço legado deve continuar funcionando enquanto a nova camada é corrigida.

## Limitações

O arquivo não autoriza execução no host nem contém credenciais. O caminho `/opt/mago-platform` precisa ser conferido no servidor antes de operar, pois a auditoria anterior acessou apenas o clone versionado e superfícies públicas.
