# Pacote de primeiro valor — Mago Bot API

**Objetivo:** permitir que uma organização conecte um canal Evolution de laboratório, receba a primeira conversa, atribua a um agente e responda usando apenas a fachada pública do Mago Bot, sem SSH, SQL manual ou edição de `.env`.

## Decisão de produto

A conta `owner` possui todos os privilégios customer-scoped sobre tenants ativos e poderes adicionais de plataforma. O owner pode provisionar uma nova organização, membership, assinatura trial, projeto e fila inicial pela Operations Console. A mutation owner-only exige MFA habilitado; o enrollment do MFA fica fora do caminho automático e deve ser concluído pelo proprietário em seu autenticador.


O Mago Bot terá uma experiência unificada para Meta Cloud e Evolution, mas providers separados no runtime. O cliente trabalha com organizações, canais, contatos, conversas e mensagens. O adapter é responsável por diferenças de QR, templates, mídia, status e conexão.

Evolution será apresentado como **provider de compatibilidade premium**, sujeito à estabilidade da sessão e às políticas do WhatsApp. Meta Cloud será apresentado como **provider oficial**, com WABA, Phone Number ID e regras oficiais da Meta. Nenhum token ou payload bruto de provider aparece no frontend, OpenAPI público, log ou webhook downstream.

## Fluxo de primeiro valor

1. A organização cria ou acessa seu workspace.
2. O cliente cria um projeto usando UUID público.
3. O cliente inicia um canal Evolution com nome amigável e provider explícito.
4. A API retorna estado `provisioning`, `connecting` ou `connected`; QR e pairing são temporários, nunca persistidos em claro.
5. O cliente configura webhook e escolhe a fila padrão.
6. Um evento inbound cria ou atualiza contato e conversa dentro da organização.
7. Um agente visualiza a timeline, assume, transfere, coloca em espera, resolve ou reabre a conversa; o envio de resposta usa a API pública de mensagens com `Idempotency-Key` até o composer de inbox ser fechado.
8. A API retorna status normalizado, correlation ID e uso contabilizado.

Cada etapa é idempotente e retomável. Falhas ficam associadas ao canal, sem derrubar outros tenants ou providers.

## Contrato customer-scoped

| Domínio | Rotas principais | Autorização |
|---|---|---|
| Canais | `GET/POST /v1/organizations/{organization_id}/channels`, `GET/PATCH /v1/channels/{channel_id}`, `connect`, `qr`, `status`, `disconnect`, `reconnect`, `DELETE` | Sessão + membership |
| Onboarding | `GET /v1/onboarding?project_id={project_uuid}`, `POST /v1/onboarding/simulate` | Sessão + membership |
| Conversas | `GET/POST /v1/conversations?project_id={project_uuid}`, timeline e status | API key escopada |
| Inbox | `GET /v1/platform/inbox/conversations`, detalhe, claim, assign, release, snooze, resolve, reopen e notes | Sessão + membership |
| Mensagens | `POST/GET /v1/messages?project_id={project_uuid}` | API key + scope; composer visual pendente |
| Webhooks | Subscription, health, replay e eventos normalizados | Sessão/membership ou assinatura |

IDs públicos são UUIDs. IDs sequenciais internos nunca são aceitos no contrato de produto. Toda mutação usa `Idempotency-Key`, `X-Request-Id`, envelope de erro e `retryable` quando aplicável.

## Critérios de aceite P0.1

Uma organização de teste deve conseguir criar um canal, consultar status, obter QR/pairing temporário, reconectar e remover o canal sem acessar o provider bruto. O backend deve rejeitar acesso a canal de outra organização com 404 ou 403 sem revelar sua existência. O QR deve expirar e não aparecer em listagem. O status deve diferenciar `provisioning`, `connecting`, `connected`, `degraded`, `disconnected`, `failed` e `deleted`.

## Critérios de aceite P0.2

Um webhook Evolution válido deve ser persistido uma única vez por `organization_id + channel_id + provider_event_id`, normalizado para o Conversation Core e entregue ao downstream com assinatura. A mesma mensagem repetida não cria segundo contato, conversa ou evento. O envio repetido com a mesma chave de idempotência não cria segunda mensagem.

## Critérios de aceite P0.3

O inbox mínimo já permite listar conversas, consultar timeline, assumir, transferir, liberar, colocar em espera, resolver, reabrir e registrar notas. O composer visual que chama o envio de mensagem com API key e idempotência é o próximo fechamento do pacote. Ações de distribuição geram auditoria com agente, fila, estado e correlation ID.

## Não faz parte deste pacote

Checkout real, CRM avançado, flows versionados, RAG, copilot, QA/ROI completo e promessa de SLA da Meta ficam fora do primeiro valor. Eles entram depois que o caminho de mensagem estiver confiável, observável e testado.

## Gate operacional atual

O runtime de produção e a fachada do produto estão promovidos. O gate restante antes de criar o tenant do laboratório é o MFA da conta owner. Depois do enrollment, a organização e o projeto do laboratório devem ser criados pelo endpoint owner-only ou pelo formulário da Operations Console, nunca com SQL manual. O QR/pairing e o número exclusivo permanecem em laboratório até o E2E opt-in confirmar webhook, inbox, idempotência, entrega e auditoria.

## Definition of Done

O pacote só é considerado pronto quando o E2E com dois tenants e provider fake/laboratório prova isolamento, idempotência, webhook duplicado, reconexão, erro normalizado, health e rollback. Uma documentação bonita sem esse teste é só maquiagem técnica.
