# API Mago Bot — Guia de acesso e operação em produção

Atualizado em 26/08/2026. Este documento não contém segredos. As chaves reais ficam somente no servidor, com permissão `600`.

## Endereços publicados

- Produto/API e portal customer-scoped: `https://app.mago-bot.com`
- Administração: `https://app.mago-bot.com/admin`
- OpenAPI: `https://app.mago-bot.com/docs`
- Referência da plataforma: `https://app.mago-bot.com/v1/reference`
- Operations Console e provider Evolution compatibilidade: `https://evo-api.mago-bot.com`
- Manager bruto da Evolution: `https://evo-api.mago-bot.com/manager` — bloqueado externamente
- Banco da plataforma: somente localhost em `127.0.0.1:33366`

## Onde estão as credenciais

No servidor, o arquivo principal é:

```bash
ssh root@107.150.35.226
chmod 600 /opt/mago-platform/CREDENCIAIS_ACESSO.txt
less /opt/mago-platform/CREDENCIAIS_ACESSO.txt
```

Arquivos de configuração protegidos:

- `/opt/mago-platform/service.env`
- `/opt/mago-platform/platform-db.env`
- `/opt/mago-platform/evolution-db.env`
- `/opt/mago-platform/evolution.env`
- `/opt/mago-platform/CREDENCIAIS_ACESSO.txt`

Não enviar esses arquivos para Git, chat, ticket, navegador ou backup público. Depois do primeiro acesso administrativo, as credenciais devem ser rotacionadas e o arquivo atualizado.

## Autenticação

Rotas administrativas da plataforma usam o cabeçalho `x-admin-token`. Rotas de cliente usam a licença emitida pela plataforma. A Evolution usa o cabeçalho `apikey`.

Exemplos sem expor valores no histórico do shell:

```bash
TOKEN=$(ssh root@107.150.35.226 "sed -n 's/^LICENSE_ADMIN_TOKEN=//p' /opt/mago-platform/service.env")
curl -fsS https://app.mago-bot.com/v1/plans -H "x-admin-token: $TOKEN"

EVOLUTION_KEY=$(ssh root@107.150.35.226 "sed -n 's/^AUTHENTICATION_API_KEY=//p' /opt/mago-platform/evolution.env")
curl -fsS https://evo-api.mago-bot.com/instance/fetchInstances -H "apikey: $EVOLUTION_KEY"
```

## Comandos de operação

```bash
ssh root@107.150.35.226
cd /opt/mago-platform
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs --tail=100 licensing-app
docker-compose -f docker-compose.production.yml logs --tail=100 evolution-api
docker-compose -f docker-compose.production.yml restart licensing-app
docker-compose -f docker-compose.production.yml restart evolution-api
```

Para atualizar a aplicação após uma alteração do código:

```bash
cd /opt/mago-platform
docker-compose -f docker-compose.production.yml up -d --build licensing-app
```

Para a Evolution, manter a versão fixada no Compose, fazer backup dos bancos e ler as notas oficiais antes de alterar `v2.3.7`.

## Arquitetura instalada

- `mago_licensing_app`: FastAPI/Gunicorn, publicado internamente em `127.0.0.1:4349`.
- `mago_evolution_api`: Evolution API `v2.3.7`, publicado internamente em `127.0.0.1:4348`.
- `mago_platform_db`: PostgreSQL da plataforma, volume Docker persistente e host port `33366` restrita a localhost.
- `mago_evolution_db`: PostgreSQL exclusivo da Evolution, sem porta pública.
- `mago_platform_redis`: Redis da plataforma.
- `mago_evolution_redis`: Redis exclusivo da Evolution.
- Nginx/aaPanel: termina TLS e encaminha os dois domínios aos serviços internos.

Os bancos e Redis são separados para impedir que carga, migração ou falha da Evolution derrube a central de licenças. Os dados ficam em volumes Docker persistentes; ainda é obrigatório configurar backup externo antes de produção comercial.

## Estado real da entrega

Pronto:

- dois domínios HTTPS publicados;
- central pública, `/admin`, `/docs`, `/v1/info` e emissão/validação de licenças;
- Evolution API instalada e respondendo na versão fixada;
- PostgreSQL e Redis separados por produto;
- chave SSH sem senha para manutenção;
- credenciais geradas aleatoriamente e fora do repositório;
- portas dos serviços expostas apenas em localhost;
- `nginx -t` validado.

Ainda não significa produto WhatsApp completo:

- não há conexão de número WhatsApp ativa;
- o webhook global da Evolution está desligado até existir um adaptador testado para a aplicação;
- billing, rate limit por cliente, métricas e fila de mensagens precisam ser finalizados antes de vender volume;
- a Meta Cloud API oficial ainda deve ser criada como trilho separado, com Business Manager, app, WABA, templates e aprovação.

## Checklist antes de alugar acesso

1. Criar backup restaurável dos dois PostgreSQL e testar restauração.
2. Configurar monitoramento de CPU, memória, disco, Redis, PostgreSQL, latência, erros 4xx/5xx e reinícios.
3. Implantar rate limit, quotas por licença e circuit breaker para impedir cascata de falhas.
4. Testar criação de instância, QR, envio, recebimento, mídia, webhook e reconexão.
5. Configurar política de retenção e remoção de mensagens, logs e sessões.
6. Rotacionar os segredos iniciais e restringir o SSH por firewall/IP quando possível.
7. Usar a Meta Cloud API oficial para clientes que exigirem conformidade, estabilidade e escala oficial.

## Referência de implantação

- Compose: `service/deploy/docker-compose.production.yml`
- Variáveis de exemplo: `service/deploy/*.env.example`
- Proxies Nginx: `service/deploy/nginx/`
- Planejamento: `PLANO_MIGRACAO_SERVIDOR_10715035226.md`
- Auditoria: `AUDITORIA_TECNICA_OPERACIONAL.md`
- Plano de produto: `PLANO_PRODUTO_API_WHATSAPP_ALUGUEL.md`
