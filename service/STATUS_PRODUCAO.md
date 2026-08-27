# Status de Produção — API Mago Bot (snapshot histórico)

Data de referência: 2026-08-27

> **Nota de identidade:** este documento preserva o retrato histórico da fundação de licenças. O produto atual é a **API Mago Bot — Produto de API**; licenças são uma camada legada e não substituem API keys customer/project-scoped.

## Atualização operacional — 2026-08-27

O rebrand e a separação de produto foram publicados na branch `feat/api-mago-bot-rebrand` do repositório `appapiwppmago` (GitHub redirecionado para `api-mago-bot`). O commit de identidade inicial é `6a3cb8b`; o commit efetivamente promovido, incluindo a landing servida pelo FastAPI com links explícitos para as superfícies corretas, é `959d367` (`clarify API Mago Bot product surfaces`). A `main` não foi alterada nem mergeada automaticamente.

| Superfície | URL | Estado verificado |
|---|---|---|
| Landing e portal customer da API | `https://app.mago-bot.com/` e `/admin` | Produção respondendo; título e identidade API Mago Bot conferidos |
| Documentação OpenAPI/Swagger | `https://app.mago-bot.com/docs` | Produção respondendo; JSON OpenAPI parseável |
| Console owner da API | `https://evo-api.mago-bot.com/ops` | Produção respondendo em host separado; login e MFA/step-up preservados |
| Produto CRM separado | `https://mago-bot.com` e `https://mago-bot.com/owner/login` | Não foi alterado neste deploy |

O canário em `127.0.0.1:4350` foi reconstruído antes da promoção, passou health live/ready, assets, landing, OpenAPI, autenticação sem credenciais e isolamento de host. O smoke P0 retornou `p0_e2e_surface=ok`, `p0_e2e_openapi=ok` e `p0_e2e_cross_surface=ok`; a fixture autenticada permaneceu não executada por ausência de credenciais de teste controladas. Em seguida, produção foi atualizada sem migrations e somente os serviços que compartilham o código foram recriados: `licensing-app`, `webhook-worker`, `owner-welcome-worker` e `evolution-health-worker`. Todos ficaram healthy, enquanto Evolution API, PostgreSQL, Redis, volumes e o CRM permaneceram fora do escopo.

Antes da promoção foram criados backups de código no VPS, sem substituir arquivos de ambiente: `/opt/mago-platform-canary/backups/service-pre-959d367-20260827T214246Z.tar.gz` e `/opt/mago-platform/backups/service-pre-959d367-20260827T214624Z.tar.gz`. O rollback previsto é retirar o upstream/release atualizado e restaurar o bundle de serviço correspondente; não há rollback destrutivo de schema porque esta entrega não contém migrations.

A validação confirma identidade, rotas, documentação e saúde do runtime. Ela **não** homologa QR, conexão de número, inbound/outbound, mídia, status, reconexão ou entrega real de WhatsApp. Meta Cloud continua sendo o provider oficial; Evolution permanece uma camada de compatibilidade até o contrato operacional ser demonstrado com número e eventos de teste autorizados.

## Resumo executivo

Este snapshot registra a fase em que o projeto funcionava principalmente como central de licenças para uma API de WhatsApp. A evolução atual é a API Mago Bot, com control plane multi-tenant, providers separados, canais, conversas, webhooks e inbox.
Ele emite, valida, revoga e audita chaves por projeto, dominio e scope.

Nota geral de prontidao para producao: **6.8/10**

Interpretacao da nota:
- Como central de licencas e controle de acesso, esta bem encaminhado.
- Como produto comercial pronto para vender com menos risco operacional, ainda faltam alguns fechamentos.
- Como "API oficial de WhatsApp" completa, ainda nao esta pronto, porque este repositorio cobre a camada de licenca, nao o motor WhatsApp em si.

## O que ja esta pronto

- API FastAPI com rotas publicas, admin e legado.
- Emissao de licenca em `POST /v1/keys`.
- Validacao de licenca em `POST /v1/keys/validate`.
- Revogacao de licenca em `POST /v1/keys/{id}/revoke`.
- Cadastro e listagem de projetos em `POST /v1/projects` e `GET /v1/projects`.
- Auditoria de eventos de emissao, validacao e revogacao.
- Catalogo publico em `GET /v1/info`.
- Referencia estruturada em `GET /v1/reference`.
- Lista de scopes em `GET /v1/scopes`.
- Painel web interno para emitir, validar e revogar chaves.
- Estrutura de banco com tabelas de projetos, licencas e auditoria.
- Docker Compose para subir app + Postgres.
- Documentacao tecnica basica no README.

## Estado atual por area

### 1. Core da licenca

Estado: bom

Pontos fortes:
- token opaco aleatorio
- hash do token no banco
- expira, revoga e audita
- suporta project slug, dominio e scope

Risco:
- nao ha assinatura criptografica de token, apenas hash no banco
- nao existe versao offline da validacao

### 2. Autenticacao administrativa

Estado: medio

Pontos fortes:
- aceita `x-admin-token`
- fallback para login de painel
- protege rotas administrativas

Risco:
- depende de segredo de ambiente para liberar o admin token
- nao ha rotacao ou politica de expiracao de sessao documentada

### 3. Documentacao publica

Estado: bom

Existe:
- landing publica em `GET /`
- catalogo em `GET /v1/info`
- referencia em `GET /v1/reference`
- scopes em `GET /v1/scopes`
- README com exemplos de uso

Risco:
- ainda falta uma documentacao orientada a integracao de terceiros, com exemplos de erro e contrato de resposta mais completo

### 4. Banco e schema

Estado: medio

Pontos fortes:
- schema SQL ja existe
- indices principais ja foram criados
- relacoes basicas estao modeladas

Risco:
- nao existe fluxo de migracao formal tipo Alembic
- o startup cria tabelas automaticamente, o que e aceitavel para boot inicial, mas nao ideal como estrategia principal de evolucao

### 5. Deploy e operacao

Estado: medio

Pontos fortes:
- `docker-compose.yml` pronto
- variaveis de ambiente definidas
- app sobe com Postgres

Risco:
- nao ha health/readiness por dependencias externas alem do health basico
- nao ha observabilidade documentada
- nao ha rate limit nem protecao explicita contra abuso no endpoint publico

### 6. Qualidade e testes

Estado: fraco

Pontos fortes:
- a aplicacao compila
- o fluxo principal esta coerente

Risco:
- nao foram encontrados testes automatizados neste repositorio
- nao existe suite de regressao para emissao, validacao, revogacao e expiracao

## O que falta para subir com mais seguranca

1. Testes automatizados dos fluxos criticos:
   - emitir licenca
   - validar licenca
   - revogar licenca
   - validar por project slug, dominio e scope
2. Migracao formal de schema para evolucao futura.
3. Rate limit e protecao contra abuso nas rotas publicas.
4. Logs estruturados e trilha de auditoria mais detalhada.
5. Documentacao de integracao para apps de terceiros.
6. Contrato mais rigido de erros da API.
7. Separar claramente o papel deste projeto:
   - ele e a central de licencas
   - o motor WhatsApp/Evolution vai consumir essa central depois

## Pontuacao por criterio

- Funcionalidade base de licencas: 8.5/10
- Documentacao publica: 7.5/10
- Estrutura de banco: 7/10
- Operacao e deploy: 6/10
- Testes e confianca de regressao: 3/10
- Prontidao para producao como SaaS de licencas: 6.8/10

## Conclusao

Se a meta e colocar um sistema de licencas no ar para controlar acesso a uma WhatsApp API, a base ja esta boa.
Se a meta e ter um produto robusto, com menos risco de quebra em producao, ainda faltam testes, governanca de schema, observabilidade e protecao de abuso.

Minha leitura final:
- **Pronto para MVP funcional de licencas:** sim
- **Pronto para vender como SaaS com risco moderado:** quase
- **Pronto para operacao mais critica sem reforcos:** ainda nao
