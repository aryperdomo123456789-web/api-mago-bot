# Mago Bot API — fachada pública do produto

## Objetivo

A fachada pública apresenta o Mago Bot como plataforma de mensageria e não como uma coleção de endpoints de provider. O consumidor usa uma API estável; Evolution e Meta Cloud permanecem adapters separados no runtime.

## Estado desta entrega

A primeira versão expõe organizações, integrações, canais, mensagens, conversas, billing, analytics e catálogo de jobs. Os recursos de leitura por sessão filtram sempre as organizações em que o usuário possui membership ativa. A API de mensagens e conversas usa API key vinculada a um único projeto e nunca atravessa o tenant da chave.

| Recurso | Método | Rota | Autorização | Estado |
|---|---|---|---|---|
| Organizações | GET | `/v1/organizations` | Sessão | Disponível |
| Integrações | GET/POST/DELETE | `/v1/integrations` | Sessão + membership | Disponível; secrets cifrados e respostas sanitizadas |
| Canais | GET | `/v1/channels` | Sessão | Disponível; inclui status e capabilities |
| Mensagem | POST | `/v1/messages?project_id={uuid}` | `X-API-Key` + `whatsapp:messages:send` | Disponível |
| Mensagens | GET | `/v1/messages?project_id={uuid}` | `X-API-Key` + `whatsapp:messages:read` | Disponível |
| Mensagem | GET | `/v1/messages/{uuid}?project_id={uuid}` | `X-API-Key` + `whatsapp:messages:read` | Disponível |
| Conversa | POST/GET | `/v1/conversations?project_id={uuid}` | API key + scope | Disponível |
| Timeline | GET/POST | `/v1/conversations/{uuid}/events?project_id={uuid}` | API key + scope | Disponível |
| Status | PATCH | `/v1/conversations/{uuid}/status?project_id={uuid}` | API key + `conversations:write` | Disponível |
| Billing | GET | `/v1/billing` | Sessão | Resumo; checkout ainda pendente |
| Analytics | GET | `/v1/analytics?days=30` | Sessão | Ledger agregado |
| Jobs | GET | `/v1/jobs` | Sessão | Catálogo; listagem detalhada pendente |
| Onboarding | GET/POST | `/v1/onboarding` e `/v1/onboarding/simulate` | Sessão + membership | Disponível; simulação não envia mensagem |

## Contrato de envio

```http
POST /v1/messages?project_id=PROJECT_UUID
X-API-Key: mb_live_<token>
X-Idempotency-Key: checkout-2026-00000001

Content-Type: application/json

{"to":"5511999999999","type":"text","text":{"body":"Olá."}}
```

`X-Idempotency-Key` deve ter pelo menos 16 caracteres. Repetir a mesma chave com payload igual retorna replay idempotente; reutilizar a chave com payload diferente retorna conflito. Cada request recebe `X-Request-ID`, `X-Trace-ID` e `traceparent`. Erros não expõem payload bruto de provider ou segredo e seguem o envelope global do middleware quando ocorre uma exceção não tratada.

## Providers

O consumidor não envia token Evolution ou token Meta. A resolução acontece no servidor por project/resource. Para Evolution, o runtime exige a instância gerenciada em estado `connected`, usa token cifrado por instância e aplica capability/erro/circuit breaker do adapter. Para Meta Cloud, o mesmo contrato encaminha para o adapter oficial e as regras de template/janela pertencem ao provider.

## Limites desta entrega

`/v1/media`, `/v1/flows` e checkout real ainda não estão liberados como recursos completos; não são anunciados como prontos apenas por existirem no roadmap. Mídia continua disponível no contrato do provider Evolution, mas upload/storage público por organização precisa de uma próxima migration e de storage assinado. O onboarding guiado e a simulação de primeiro valor estão disponíveis; criação automática de fila/flow e billing transacional ainda são próximos gates.

## Integração com o produto consumidor

O repositório `friendly-helper` analisado não chama o Mago Bot API: ele ainda usa Supabase, funções TanStack e modelos IPTV. Não deve ser conectado por suposição. O frontend real de WhatsApp precisa ser identificado ou criado para consumir este contrato; quando isso ocorrer, ele deve usar apenas a fachada Mago, nunca consultar as tabelas de produção diretamente.
