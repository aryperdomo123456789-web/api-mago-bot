# Contexto operacional para Manus

Este repositório documenta e versiona o produto Mago Bot: uma central de licenciamento para uma API WhatsApp, a infraestrutura da Evolution API e o plano de evolução para a Meta Cloud API oficial.

## Produção atual

Servidor: `107.150.35.226` (SSH como `root`, autenticação por chave já configurada na máquina de operação).

Domínios:

- Produto público e painel: `https://app.mago-bot.com`
- Evolution API: `https://evo-api.mago-bot.com`

Portas internas:

- Aplicação de licenças: `127.0.0.1:4349`
- Evolution API: `127.0.0.1:4348`
- PostgreSQL da plataforma: `127.0.0.1:33366`
- PostgreSQL da Evolution: somente rede Docker
- Redis: somente redes Docker

Diretório de produção: `/opt/mago-platform`.

## Serviços Docker

- `mago_licensing_app`: FastAPI/Gunicorn, emissão, validação e revogação de licenças.
- `mago_platform_db`: PostgreSQL exclusivo da plataforma.
- `mago_platform_redis`: Redis da plataforma.
- `mago_evolution_api`: Evolution API v2.3.7.
- `mago_evolution_db`: PostgreSQL exclusivo da Evolution.
- `mago_evolution_redis`: Redis exclusivo da Evolution.

O Compose está em `service/deploy/docker-compose.production.yml`. As variáveis reais ficam no servidor em arquivos com permissão 600 e nunca devem ser commitadas.

## Acesso e segredos

O inventário de credenciais está somente no servidor:

`/opt/mago-platform/CREDENCIAIS_ACESSO.txt`

Ele contém o token administrativo da plataforma, a chave `apikey` da Evolution, o usuário inicial do painel e os dados dos bancos. Não copiar os valores para este repositório, issues ou logs.

## Como validar

```bash
ssh root@107.150.35.226
cd /opt/mago-platform
docker-compose -f docker-compose.production.yml ps
curl -fsS https://app.mago-bot.com/health
curl -fsS https://evo-api.mago-bot.com/
```

## Limites conhecidos

A infraestrutura e a central de licenças estão funcionando. Ainda não é permitido afirmar que existe uma API WhatsApp comercial completa: é necessário conectar números, validar QR/sessões, implementar o adaptador de webhook, filas, rate limit por cliente, métricas, backups restauráveis e políticas de retenção. A Meta Cloud API deve permanecer como trilho separado para clientes oficiais.

## Regras para mudanças do Manus

1. Não alterar produção sem backup e plano de rollback.
2. Não expor ou rotacionar segredos sem registrar a mudança no inventário seguro do servidor.
3. Fixar versões de imagens e dependências.
4. Validar `docker-compose config`, testes HTTP e `nginx -t` antes do deploy.
5. Não ativar webhook global da Evolution apontando para endpoint inexistente.
6. Registrar decisões, portas, migrações e impacto no documento operacional.

## Documentação de referência

- `service/GUIA_ACESSO_E_OPERACAO_PRODUCAO.md`
- `service/AUDITORIA_TECNICA_OPERACIONAL.md`
- `service/PLANO_MIGRACAO_SERVIDOR_10715035226.md`
- `service/PLANO_PRODUTO_API_WHATSAPP_ALUGUEL.md`
- `service/README.md`
