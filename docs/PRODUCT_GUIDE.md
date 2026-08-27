# API Mago Bot — Guia de Produto e API

**Versão do contrato:** 1.0
**Data:** 26 de agosto de 2026
**Autor:** Manus AI

> **Posicionamento:** a API Mago Bot é um produto multi-tenant de operação de mensagens e conversas. Meta Cloud é o provider oficial. Evolution é um provider de compatibilidade premium para laboratório, atendimento opt-in e operações controladas. A experiência pode ser unificada; as garantias, políticas, autenticação e semântica do provider continuam separadas.

## 1. O produto

A API Mago Bot organiza a operação em **organização**, **projeto**, **provider**, **canal**, **contato**, **conversa**, **mensagem**, **fila** e **webhook**. O control plane concentra autenticação, autorização, idempotência, quotas, auditoria, tracing, retries, circuit breaker e normalização de erros. O cliente integra uma superfície estável da API Mago Bot sem acessar diretamente a Evolution API, credenciais globais ou bancos internos.

O produto foi desenhado para que a primeira ativação seja operacionalmente guiada: criar um workspace, escolher um provider, conectar o canal, configurar a fila, receber a primeira conversa e responder com rastreabilidade. A meta de paridade é de **experiência operacional**, e não de equivalência regulatória, de transporte ou de SLA com a Meta.

## 2. Duas camadas de provider

| Camada | Uso | Credenciais | Limites comerciais |
|---|---|---|---|
| Meta Cloud | Operação oficial com WABA e Phone Number ID | Guardadas e cifradas por organização/projeto | Sujeita às políticas, templates, limites e disponibilidade da Meta |
| Evolution | Compatibilidade premium para sessão, QR/pairing e laboratório | Token global e tokens de instância server-side | Não é a WhatsApp Business Platform oficial; estabilidade depende da sessão/provider |

A camada Meta Cloud deve ser escolhida para operações que dependem das garantias oficiais, políticas de template e previsibilidade da plataforma. A camada Evolution pode acelerar pilotos e operações controladas, mas não deve ser apresentada como “API oficial alternativa”. A API Mago Bot não promete que a Evolution reproduzirá políticas, qualidade, revisão ou SLA da Meta.

## 3. Modelo de acesso

A conta **owner** é wildcard administrativo. Ela pode usar os recursos customer-scoped de tenants ativos e, além disso, criar tenants, memberships, assinaturas, projetos, filas, planos, integrações, canais e políticas operacionais conforme os scopes disponíveis. A conta owner não é um bypass: usa sessão revogável, host correto, auditoria e MFA para mutations críticas.

Usuários comuns trabalham apenas com memberships explícitos. `tenant_owner` administra o próprio tenant; `tenant_admin` opera o workspace; `tenant_developer` integra API e webhooks; `tenant_billing` acessa billing; `tenant_readonly` possui leitura limitada. `platform_support` tem leitura operacional restrita e `platform_partner` não recebe acesso global por padrão.

| Superfície | Host | Acesso principal |
|---|---|---|
| Portal cliente e API de produto | `app.mago-bot.com` | Sessão ou API key com membership/scopes |
| Operations Console e lifecycle | `evo-api.mago-bot.com` | Owner, superadmin, operator e suporte conforme a ação |
| Manager bruto do provider | Não público | Bloqueado externamente; não faz parte do produto |

IDs públicos usam UUID. IDs sequenciais internos não fazem parte do contrato público. Um recurso de outro tenant deve retornar 403 ou 404 sem revelar existência, payload ou credencial.

## 4. Primeiro valor

O fluxo recomendado para um piloto é o seguinte:

1. O owner conclui MFA no autenticador e entra na Operations Console.
2. Em **Clientes / Tenants**, cria a organização e o projeto do laboratório com provider explícito `evolution`; a transação cria membership do owner, assinatura trial e fila inicial opcional.
3. Em **Evolution / Compatibilidade**, cria o canal com nome amigável e inicia QR ou pairing conforme o flavor disponível.
4. O operador acompanha estados `provisioning`, `created`, `qr_pending`, `connecting`, `connected`, `degraded`, `disconnected`, `failed` e `deleted`.
5. A API Mago Bot configura o callback gerenciado e normaliza eventos inbound no Conversation Core.
6. O agente abre o inbox, faz claim ou assignment, registra nota e responde com idempotência.
7. O owner observa health, auditoria, usage e falhas antes de considerar a troca do número de laboratório pelo número de produção.

QR, pairing, token de instância, API key global e segredo de webhook são dados operacionais sensíveis. Eles não devem ser enviados pelo chat, incluídos em logs ou publicados em documentação.

## 5. Contrato de headers

Toda mutation de integração deve enviar `Idempotency-Key`. O cliente pode enviar `X-Request-Id` para correlação; se não enviar, a API Mago Bot gera um request ID. API keys devem possuir apenas os scopes necessários.

```http
Authorization: Bearer <session-or-token>
X-API-Key: mb_live_<redacted>
Idempotency-Key: onboarding-lab-0001
X-Request-Id: req_<client-generated>
Content-Type: application/json
```

O mesmo `Idempotency-Key` com payload equivalente retorna o resultado já registrado. Reutilizar a chave para outro payload deve ser rejeitado. Retries só devem ser feitos para erros marcados como retryable ou respostas 429/5xx conforme backoff indicado.

## 6. Envelope de erro

O cliente deve tratar erros pelo código e não pelo texto livre. O formato esperado contém `error.code`, `error.message`, `error.retryable` e `request_id` quando disponível.

```json
{
  "error": {
    "code": "provider_unavailable",
    "message": "O provider não respondeu dentro do timeout.",
    "retryable": true
  },
  "request_id": "req_example"
}
```

Erros de autenticação, membership, payload inválido ou recurso inexistente não devem entrar em retry cego. Um erro de provider pode ser temporário, mas o circuito do provider e o ledger de uso pertencem à API Mago Bot.

## 7. Superfícies de API

| Domínio | Exemplos | Proteção |
|---|---|---|
| Organizações | `GET /v1/organizations` | Sessão + membership; owner wildcard |
| Integrações | `GET/POST /v1/integrations` | Scopes + credenciais cifradas |
| Canais | `GET/POST /v1/organizations/{organization_id}/channels`, status e lifecycle | Membership, provider explícito e auditoria |
| Mensagens | `GET/POST /v1/messages` | API key, scope, quota e idempotência |
| Conversas | `GET /v1/conversations` | Tenant/project scope |
| Inbox | `GET /v1/platform/inbox/queues` e ações de assignment | Sessão + membership |
| Onboarding | `GET /v1/onboarding`, `POST /v1/onboarding/simulate` | Sessão + project scope |
| Webhooks | Endpoint Evolution secreto e subscriptions downstream | Deduplicação, sanitização e assinatura |
| Billing/Analytics | Rotas de billing, usage e métricas | Tenant scope e papel adequado |
| Operations | `/v1/ops/*` | Host operacional e papel de plataforma |

A documentação OpenAPI deve confirmar paths, métodos, scopes e respostas sem incluir propriedades de `secret`, `password`, `apikey` ou tokens de provider em schemas públicos.

## 8. Evolution seguro

A Evolution API permanece atrás do adapter de management e do adapter de envio. A instalação atual de produção utiliza Evolution API v2; o suporte a Evolution Go é um flavor separado e não deve ser alternado em uma instância existente sem revalidar endpoint, autenticação e payload.

O webhook gerenciado usa `POST /v1/webhooks/evolution/{instance_uuid}/{endpoint_secret}`. O segredo é comparado em tempo constante, o payload é limitado e sanitizado, e o evento é deduplicado por instância/provider event ID. Eventos de mensagem seguem para o Conversation Core; delivery downstream usa outbox e worker. O health worker consulta a instância e atualiza estado, mas não reconecta automaticamente para evitar loops.

## 9. Inbox e primeiro atendimento

O inbox mínimo cobre filas, assignment, claim, release, assign, snooze, resolve, reopen, notas, detalhe e timeline. Cada ação deve carregar tenant, conversa, agente, estado anterior, estado novo, request ID e resultado na auditoria. O envio do composer deve usar a mesma chave de idempotência do contrato público e nunca depender de token exposto no browser.

## 10. Operação e rollback

Toda promoção deve fazer backup antes de alterações, aplicar migrations idempotentes uma a uma, testar o Compose efetivo do host, reconstruir somente os serviços afetados e aguardar healthchecks completos. DB, Redis, Evolution API e volumes não devem ser reiniciados sem necessidade. Rollback de código pode restaurar o artefato anterior; migrations aplicadas são forward-only e não devem ser removidas destrutivamente como primeira reação.

O Manager bruto continua bloqueado. O proxy do webhook deve apontar ao FastAPI antes do fallback da Evolution, e o Nginx deve ser testado com o binário efetivo do aaPanel antes de reload gracioso.

## 11. Prontidão atual e próximos gates

O runtime Primeiro Valor, owner wildcard, health worker, onboarding, inbox mínimo e provider Evolution separado estão promovidos e validados em produção. O Overview também degrada com segurança quando a camada opcional Resend não está instalada.

O **MFA owner** continua pendente. Até concluir o enrollment, a criação de tenant/projeto do laboratório permanece bloqueada intencionalmente. Depois do MFA, faltam o E2E autenticado com o número de laboratório, confirmação de webhook/inbox/mensagem opt-in, teste de restore isolado, política de suporte/SLA e o fechamento do composer visual.

A definição de produto vendável deve ser baseada no que foi verificado, não em promessa. A plataforma está pronta para pilotos controlados e evolução comercial, mas ainda não deve declarar entrega real de WhatsApp, SLA oficial ou escala ilimitada sem os gates acima.

## Referências

[1]: https://developers.facebook.com/docs/whatsapp/cloud-api "Meta WhatsApp Cloud API — documentação oficial"

[2]: https://docs.evolutionfoundation.com.br/evolution-go "Evolution Go — documentação oficial"

[3]: https://github.com/evolution-foundation/evolution-go "Evolution Go — repositório oficial"
