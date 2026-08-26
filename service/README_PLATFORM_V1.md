# Mago Bot Platform — API v1

**Status:** foundation implementada em `feat/platform-api-v1`  
**Objetivo:** fornecer uma API própria para operações WhatsApp, com provider oficial Meta Cloud API e adapter de compatibilidade Evolution explicitamente separado.

> A plataforma Mago Bot não é a API oficial da Meta. Ela é um control plane e gateway de produto que normaliza recursos, tenants, chaves, quotas e eventos. O provider oficial continua sendo a WhatsApp Business Platform Cloud API.

## Primeiro fluxo de produção

O operador aplica `service/sql/migrations/0001_platform_foundation.sql` no PostgreSQL de staging, injeta os segredos server-side de `service/deploy/service.env.example`, inicia a aplicação e o worker de webhooks, cria ou confirma o tenant, cria um projeto, vincula o Phone Number ID Meta como recurso e emite uma API key com scopes mínimos.

A Meta orienta criar um app WhatsApp, conectar um WABA, guardar o WABA ID e o Phone Number ID, usar um System User com token permanente e configurar um endpoint de webhook próprio para produção.[1] O Mago Bot guarda os tokens apenas no servidor e recebe callbacks em `/v1/webhooks/meta`.

## Endpoints implementados

| Grupo | Endpoint | Autorização | Função |
|---|---|---|---|
| Auth | `POST /v1/platform/auth/signup` | Pública | Cria usuário, tenant, membership e trial; exige confirmação de email |
| Auth | `POST /v1/platform/auth/verify-email` | Pública | Consome token de confirmação uma vez |
| Auth | `POST /v1/platform/auth/login` | Pública | Cria sessão opaca server-side e cookie `__Host-` |
| Auth | `POST /v1/platform/auth/password-reset/*` | Pública | Solicita e conclui reset de senha |
| Tenant | `GET /v1/platform/tenants/me` | Sessão | Lista tenants do usuário |
| Projeto | `GET/POST /v1/platform/projects` | Sessão + membership | Lista/cria projeto filtrando tenant |
| Recursos | `GET/POST /v1/platform/projects/{id}/resources` | Sessão + permission | Vincula provider resource; segredo não é aceito nesse endpoint |
| Keys | `POST /v1/platform/projects/{id}/keys` | Sessão + `key:manage` | Cria key; token em claro aparece uma única vez |
| Keys | `GET /v1/platform/projects/{id}/keys` | Sessão + `key:manage` | Lista prefixos e status, nunca tokens |
| Mensagens | `POST /v1/projects/{id}/messages` | `X-API-Key` + scope | Envia mensagem e aplica quota/idempotência |
| Mensagens | `GET /v1/projects/{id}/messages*` | `X-API-Key` + scope | Consulta status/lista de mensagens do próprio projeto |
| Webhook Meta | `GET/POST /v1/webhooks/meta` | Challenge/HMAC | Verifica endpoint e recebe eventos Meta |
| Webhook cliente | `/v1/platform/projects/{id}/webhooks*` | Sessão + permission | Configura, lista, gira e desativa endpoint do cliente |
| Uso | `GET /v1/platform/usage` | Sessão + `usage:read` | Exibe contadores, ledger diário e limites do plano |
| Ledger | `GET /v1/platform/usage/ledger` | Sessão + `usage:read` | Lista consumo append-only auditável por tenant |
| Conversas | `POST/GET /v1/projects/{id}/conversations` | `X-API-Key` + scope | Abre/lista conversas e resolve identidade do cliente |
| Timeline | `GET/POST /v1/projects/{id}/conversations/{uuid}/events` | `X-API-Key` + scope | Lista ou adiciona eventos normalizados com idempotência |
| Lifecycle | `PATCH /v1/projects/{id}/conversations/{uuid}/status` | `X-API-Key` + scope | Atualiza estado e registra evento de status |
| Operação | `/health/live`, `/health/ready`, `/metrics` | Métricas com token | Liveness, readiness de banco e métricas protegidas |

## Envio de mensagem

A chamada exige `X-Idempotency-Key` com pelo menos 16 caracteres. A chave é associada ao tenant e ao projeto; repetir a mesma chave com o mesmo payload retorna replay idempotente, enquanto reutilizar a chave com payload diferente retorna conflito. O sistema aplica limites próprios de minuto/dia e não tenta ultrapassar os limites Meta.

A resposta não retorna o token Meta nem o payload cru do provider. O provider retorna seu message ID e o Mago Bot persiste apenas os dados necessários para status e diagnóstico. A política padrão do primeiro corte suporta texto; templates, mídia e interativos entram por capability explícita do adapter.

## Conversation Core

O Conversation Core transforma a mensagem isolada em uma conversa contínua. `CustomerProfile` representa o cliente dentro do tenant; `CustomerIdentity` liga telefone, WhatsApp, email, SIP ou identificador externo ao perfil; `Conversation` mantém canal primário, subject, external reference e lifecycle; `ConversationEvent` é a timeline append-only para mensagem, status, handoff, nota, insight e eventos do sistema. A API pública exige scopes `conversations:write` e `conversations:read`.

`POST /v1/projects/{id}/conversations` resolve ou cria a identidade no tenant e reusa uma conversa aberta quando a mesma `external_ref` é enviada. `POST /v1/projects/{id}/conversations/{uuid}/events` exige `X-Idempotency-Key`; o primeiro evento retorna 201 e um replay idêntico retorna 200 sem duplicar a timeline. O envio outbound aceita `conversation_id` opcional, cria eventos `message.accepted` e `message.sent/failed`, e mantém o histórico unificado sem quebrar clientes legados.

## Webhooks

A Meta documenta payloads de até 3 MB e retentativas por até sete dias quando o endpoint não retorna HTTP 200; duplicatas são possíveis.[2] O endpoint Mago Bot valida `X-Hub-Signature-256`, deduplica por provider/event ID, mapeia Phone Number ID para recurso/tenant e grava o evento. Deliveries de saída são colocadas em outbox e processadas pelo `app.webhook_worker`, com HMAC `X-Mago-Signature`, retries exponenciais e estado `dead_letter` após o máximo configurado. O cadastro e o worker bloqueiam endpoints sem HTTPS/443, credenciais na URL, loopback, RFC1918, link-local, metadata services, hosts internos e resoluções não globais; redirects não são seguidos.

## Segurança por padrão

Sessões do control plane são opacas, armazenadas somente como hash no banco, revogáveis e protegidas por cookie HttpOnly, Secure, SameSite Lax e prefixo `__Host-`. API keys também são armazenadas somente como hash; o token é exibido no momento de criação e não volta em listagens. Segredos de webhook são cifrados com Fernet via `PLATFORM_SECRET_KEY`.

Cada rota de negócio resolve tenant no servidor e rejeita projeto fora do tenant da key. Papéis são enumerados e desconhecidos são negados. O middleware adiciona request ID, HSTS, `nosniff`, frame denial, Referrer Policy, Permissions Policy e CSP. O endpoint de métricas exige token dedicado de pelo menos 32 caracteres.

## Limites externos da primeira versão

O onboarding Embedded Signup, aprovação App Review, cobrança real, rotação automática de System User tokens, templates CRUD, mídia, analytics avançado, circuit breaker distribuído e mTLS ainda precisam ser concluídos antes de vender escala enterprise. O primeiro deploy deve usar WABA/Phone Number de teste e provider Meta Cloud com credenciais do proprietário. Evolution não deve ser anunciado como “API oficial”.

A Meta informa que portfolios recém-criados começam com limite de 250 usuários únicos fora da janela de atendimento e que telefones têm throughput padrão de até 80 mensagens por segundo, além de limite de pareamento de aproximadamente uma mensagem a cada seis segundos para o mesmo usuário.[3] Esses números são limites do provider, não promessa do Mago Bot; o produto deve monitorar e recusar excesso com erro explícito.

## Configuração mínima

| Variável | Regra |
|---|---|
| `PLATFORM_SESSION_SECRET` | Aleatório, mínimo de 32 caracteres |
| `PLATFORM_SECRET_KEY` | Chave Fernet válida, gerada fora do repositório |
| `META_SYSTEM_USER_TOKEN` | Token permanente server-side, nunca no frontend |
| `META_APP_SECRET` | App Secret para assinatura de webhook |
| `META_WEBHOOK_VERIFY_TOKEN` | Token de challenge do endpoint Meta |
| `META_GRAPH_API_VERSION` | Versão Graph definida pelo operador; exemplo atual `v26.0` |
| `METRICS_TOKEN` | Segredo dedicado para scrape de métricas |
| `PLATFORM_AUTO_CREATE_SCHEMA` | `false` em produção; migração explícita |

## Testes locais executados

A entrega inclui `verify_platform_baseline.py`, `verify_platform_contracts.py`, `verify_schema_fresh.py`, `verify_operational_contracts.py` e `verify_message_ledger_ssrf.py`. Eles verificam compilação Python, sintaxe JavaScript, rotas OpenAPI, schemas PostgreSQL em mock, hashing, idempotência, cifragem, assinatura de webhook, headers, migração transacional, vínculo de mensagem, ledger e SSRF.

## Referências

[1]: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started "Meta — WhatsApp Cloud API Get Started"
[2]: https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview "Meta — WhatsApp Webhooks"
[3]: https://developers.facebook.com/documentation/business-messaging/whatsapp/about-the-platform "Meta — About the WhatsApp Business Platform"

## Integração WhatsApp do proprietário

O portal seguro em `/platform` possui a aba `WhatsApp do dono`, disponível apenas para o owner e papéis de plataforma autorizados. A aba salva `Phone Number ID`, `WABA ID`, token Meta, App Secret e verify token através do backend. Os três segredos são cifrados com Fernet em repouso e nunca são retornados ao navegador; campos secretos vazios preservam o valor existente.

`GET /v1/platform/owner/whatsapp` retorna somente estado mascarado. `PUT /v1/platform/owner/whatsapp` cria ou atualiza a configuração. `POST /v1/platform/owner/whatsapp/test` consulta o perfil do número na Graph API, atualiza nome verificado, telefone, qualidade e estado conectado. `POST /v1/platform/owner/whatsapp/disconnect` remove os segredos cifrados, desliga boas-vindas e marca a integração como desconectada.

A boas-vindas automática não dispara apenas porque um visitante informou telefone. O cadastro precisa conter telefone válido, checkbox de opt-in marcado e origem do consentimento; a integração owner precisa estar conectada, habilitada e ter template aprovado. O signup seguro enfileira a intenção depois da confirmação de email; o trial público enfileira após a criação com opt-in explícito. A fila `owner_welcome_deliveries` deduplica por origem e é processada por `app.owner_welcome_worker`, que usa somente template Meta, retry exponencial, limite de tentativas e dead letter. A resposta aceita pela Meta não é tratada como entrega final; o status real depende de webhook.

O Compose de staging e produção contém o worker preparado, mas a execução no ambiente produtivo só deve ocorrer após aplicar a migration `0004_owner_whatsapp_welcome.sql`, preencher secrets diretamente no secret manager e validar WABA/Phone Number de teste. QR code, scraping ou sessão WhatsApp Web não fazem parte do conector oficial.
