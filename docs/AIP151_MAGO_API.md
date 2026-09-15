# Aplicação do Google AIP-151 à API Mago Bot

**Produto:** API Mago Bot — produto de API multi-tenant

**Escopo:** operações Evolution/Meta Cloud, mensagens, webhooks, onboarding, inbox, workers, idempotência e jobs futuros.

**Status deste documento:** análise arquitetural e plano de aplicação. Nenhuma migration ou mudança de runtime é executada apenas pela leitura deste documento.

## 1. Conclusão executiva

A API Mago Bot já possui uma base acima da média para adotar operações assíncronas: autenticação por API key, escopos, quotas, rate limit distribuído, circuit breaker, tracing, auditoria, `Idempotency-Key`, tabelas de outbox/webhook delivery, workers separados e estados persistentes de instâncias Evolution. O que falta não é criar mais endpoints aleatórios; é expor ao consumidor uma unidade pública e uniforme de trabalho assíncrono.

A recomendação é adotar AIP-151 de forma incremental, por HTTP/JSON e sem reescrever a API em gRPC. O primeiro ganho deve ser um recurso **Operation** tenant/project-scoped, com polling, metadata, resultado, erro terminal, expiração e autorização. A compatibilidade existente deve ser preservada: os endpoints síncronos continuam funcionando e o modo assíncrono entra por uma nova rota ou por negociação explícita com `Prefer: respond-async`.

> **Decisão principal:** usar `Operation` para uma execução pontual que pode ultrapassar o tempo de resposta; usar `Job` somente para configuração e execução repetível, como campanhas, flows recorrentes e sincronizações. Não transformar todo CRUD ou todo envio de mensagem em job.

## 2. Fontes normativas consultadas

| Referência | Regra principal | Aplicação no Mago |
|---|---|---|
| [AIP-151 — Long-running operations][1] | Método demorado retorna `Operation`; deve haver metadata, response type, erro terminal e serviço uniforme de Operations | Criar Operations REST/JSON para envio assíncrico, reconciliação e ações longas |
| [AIP-152 — Jobs][2] | Job é recurso configurável e repetível; `Run` retorna Operation | Reservar para campanhas, flows agendados, importações e syncs |
| [AIP-155 — Request identification][3] | `request_id` opcional garante idempotência e retry seguro; UUID é recomendado | Unificar `Idempotency-Key`, request hash, tenant, projeto e endpoint |
| [AIP-193 — Errors][4] | Erros usam status canônico, `ErrorInfo`, reason/domain e detalhes acionáveis | Evoluir envelope atual sem quebrar `error.code/message/request_id` |
| [AIP-194 — Automatic retry configuration][5] | Retry somente quando repetir é seguro; `UNAVAILABLE` é retryable, quota/argumento não | Manter circuit breaker e classificar retries por provider e efeito externo |
| [AIP-203 — Field behavior][6] | Requests devem declarar required/optional/output-only; documentação não substitui validação | Melhorar OpenAPI de operations, channels, messages e webhooks |
| [AIP-211 — Authorization checks][7] | Autorizar antes de validar e não vazar existência de recursos | Autorizar por tenant/projeto/API key antes de acessar Operation |
| [AIP-136 — Custom methods][8] | Ações mutáveis usam POST e URI `:verb`, com nomes claros | Usar `:run`, `:cancel`, `:replay` e `:retry` quando realmente necessários |
| [AIP-142 — Time and duration][9] | Timestamps absolutos e durações devem ter semântica consistente | Novos recursos usam `*_time`, `*_seconds`/Duration documentado e UTC |
| [AIP-180 — Backwards compatibility][10] | Clientes existentes não podem quebrar em mudança minor/patch | Introduzir modo assíncrono de forma aditiva e negociável |

## 3. Estado real já existente no Mago Bot

### 3.1 Primitivas que já aceleram a adoção

O módulo de mensagens já persiste `OutboundMessage`, exige `X-Idempotency-Key`, calcula hash do payload, devolve replay idempotente e separa estados `sending`, `sent` e `failed`. O mesmo fluxo aplica quota por minuto/dia, rate limit distribuído, circuit breaker, seleção explícita de provider e auditoria de timeline.

O fluxo de conversa usa `IdempotencyRecord` com chave única por tenant, endpoint e idempotency key, hash do request e replay da resposta original. Essa é a evidência mais próxima de AIP-155 no código atual.

O provider layer já diferencia `MetaCloudAdapter` e `EvolutionAdapter`, e `ProviderError` já carrega `code` e `retryable`. Meta, Evolution e Resend distinguem timeout/rede/falha temporária de rejeição permanente. O circuit breaker abre somente em falhas retryable e mantém uma janela de probe.

Webhooks já possuem entidades persistentes de evento e entrega, deduplicação por provider event ID, assinatura HMAC, SSRF protection, fila/outbox e worker com backoff e dead letter. O health worker Evolution atualiza estado de instâncias de forma assíncrona e mantém heartbeat.

### 3.2 Lacunas objetivas

A fachada pública expõe `/v1/jobs`, mas o catálogo atual retorna lista vazia e informa que a listagem detalhada entra depois. Não existe um recurso público persistente `Operation`/`Job` com `done`, `response`, `error` e `metadata`.

O envio de mensagem ainda chama o provider dentro da própria requisição. Isso é aceitável para o caminho atual de baixa latência, mas deixa o consumidor sujeito a timeout e resposta 503 quando o efeito externo é incerto. O Mago precisa de um modo assíncrono opt-in para desacoplar aceite da execução e permitir reconciliação.

O envelope global de erro atual é compacto, com `error.code`, `error.message` e `request_id`. Ele é útil, mas não oferece razão/domain, retryability, retry-after, detalhes de campo, precondition ou identificação canônica do provider.

Os modelos atuais usam nomes históricos como `created_at`, `updated_at` e `last_status_check_at`. Eles não devem ser renomeados em massa porque isso quebraria consumidores; os novos recursos devem adotar a convenção nova e documentar o mapeamento dos campos legados.

## 4. O que deve virar Operation

| Caso | Decisão | Motivo |
|---|---|---|
| `POST /v1/messages` atual | Manter síncrono por compatibilidade | Já existe cliente e retorno `201`; mudança silenciosa seria breaking |
| Envio assíncrono opt-in | **Operation** | Aceite rápido, provider pode demorar ou ficar incerto |
| Criação de instância Evolution | Pode começar síncrona; Operation se provider exceder SLA | Provisionamento inicial é curto em muitos casos, mas precisa reconciliar falha externa |
| Conexão por QR | Recurso `channel` + status/QR; não bloquear em Operation até o usuário escanear | O QR é estado de conexão e expira; o usuário controla a conclusão |
| Reconnect/logout/disconnect | Síncrono quando rápido; Operation se execução for longa | Evita inflar ações simples sem necessidade |
| Replay de webhook | Retorno imediato `pending` hoje; Operation quando houver muitas entregas | Permite acompanhar fan-out e dead letters sem timeout |
| Health polling | Worker interno + estado do canal | Não expor polling operacional como job de cliente |
| Importação de contatos | **Operation** | Trabalho potencialmente longo e reportável |
| Campanha/flow recorrente | **Job** + execuções | Configuração persistente e repetível; histórico de runs |
| Billing/exportação/analytics pesado | **Operation** ou export Job | Depende da duração e da necessidade de histórico |

## 5. Contrato-alvo recomendado

### 5.1 Recurso Operation

A representação pública deve ser estável e agnóstica de provider:

```json
{
  "name": "operations/01J...",
  "id": "01J...",
  "project_id": "7ec...",
  "kind": "message.send",
  "done": false,
  "metadata": {
    "state": "queued",
    "progress_percent": 0,
    "start_time": "2026-08-27T21:45:00Z",
    "last_update_time": "2026-08-27T21:45:00Z",
    "attempt": 0,
    "retryable": true
  },
  "response": null,
  "error": null,
  "expire_time": "2026-09-26T21:45:00Z"
}
```

Quando concluída, `done=true` e exatamente um dos campos `response` ou `error` deve estar preenchido. O erro deve usar o envelope padronizado do Mago com código canônico, `reason`, `domain`, provider code sanitizado, `retryable` e `request_id`.

A persistência mínima deve incluir UUID público, tenant/projeto, tipo, status, request hash, idempotency key, actor/API key, metadata JSON, response JSON sanitizado, error JSON sanitizado, created/start/update/complete/expire times, attempt count e vínculo opcional ao recurso afetado. Nenhum secret, token, header sensível, conteúdo completo de mídia ou credencial deve ser armazenado na Operation.

### 5.2 Endpoints REST/JSON

A primeira versão pode ser aditiva:

```text
GET    /v1/operations/{operation_id}
GET    /v1/operations?project_id={public_project_uuid}&page_size=...
DELETE /v1/operations/{operation_id}
POST   /v1/operations/{operation_id}:cancel   # somente cancelamento cooperativo real
```

O endpoint `DELETE` deve ser documentado como remoção do interesse/limpeza da Operation quando aplicável; ele não pode prometer interromper uma chamada externa já aceita pelo provider. `:cancel` só deve existir quando o worker consegue impedir a execução ou marcar a execução como cancelada antes do efeito externo.

Para iniciar um envio assíncrono sem quebrar o endpoint atual, há duas opções compatíveis:

```text
POST /v1/projects/{project_id}/messages:send
Prefer: respond-async
Idempotency-Key: UUID4
```

ou uma nova rota explicitamente assíncrona:

```text
POST /v1/projects/{project_id}/messages:sendAsync
```

A primeira opção é mais elegante para negociação, mas exige documentar o comportamento HTTP 202 e a preferência. A segunda é mais simples para SDKs e evita ambiguidade. O nome `Async` não deve ser usado como método de domínio; se essa variante existir por compatibilidade, preferir `sendLongRunning` ou negociação `Prefer` na documentação de produto.

### 5.3 Máquina de estados

Estados de Operation devem ser poucos e explícitos: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCEL_REQUESTED`, `CANCELLED`, `EXPIRED` e `ABORTED` quando houver concorrência/preempção real. Estados de provider, como `qr_pending`, `connected` e `degraded`, continuam pertencendo ao canal/instância e não devem ser confundidos com estados da Operation.

A transição deve ser monotônica para estados terminais. Atualizações concorrentes devem usar lock/version ou compare-and-set. Duas Operations paralelas para a mesma ação idempotente devem ser deduplicadas; duas ações mutuamente exclusivas devem retornar `ABORTED` ou `FAILED_PRECONDITION` com motivo acionável.

## 6. AIP-155 aplicado à idempotência

O Mago deve manter `Idempotency-Key` como header público por compatibilidade, mas definir a seguinte identidade lógica:

```text
tenant_id + project_id + endpoint + idempotency_key
```

O servidor deve persistir hash canônico do body e dos parâmetros relevantes. Repetir a mesma chave com o mesmo request retorna a resposta anterior ou a mesma Operation. Repetir a chave com body, projeto, endpoint ou recurso diferente retorna `409 IDEMPOTENCY_KEY_REUSED`.

A retenção deve ser documentada. Para operações externas e mensagens, uma janela de 24–72 horas é o mínimo operacional; para reconciliação e jobs, pode ser necessário manter o registro até a expiração da Operation. A retenção exata deve ser configurável por plano, mas nunca pode ser menor que a janela de retry prometida ao consumidor.

O registro deve ser criado antes do primeiro efeito externo. Se a chamada ao provider cair após o envio e antes da resposta, a Operation fica `RUNNING`/`UNKNOWN` e entra em reconciliação; não deve ser recriada cegamente. A reconciliação usa provider message ID, webhook ou consulta de status quando disponível.

## 7. AIP-193 aplicado ao envelope de erro

O envelope atual deve ser mantido e ampliado de forma aditiva:

```json
{
  "error": {
    "code": "provider_unavailable",
    "message": "O provider está temporariamente indisponível; tente novamente após o prazo informado.",
    "status": "UNAVAILABLE",
    "reason": "PROVIDER_UNAVAILABLE",
    "domain": "api.mago-bot.com/providers/evolution",
    "retryable": true,
    "retry_after_seconds": 30,
    "request_id": "req_...",
    "details": [
      {
        "type": "provider",
        "provider": "evolution",
        "provider_code": "provider_5xx"
      }
    ]
  }
}
```

Regras práticas:

1. `message` explica a ação ao consumidor e não revela stack trace, SQL, URL interna, token, nome de container ou segredo.
2. `reason` é estável e em UPPER_SNAKE_CASE; `domain` identifica o serviço.
3. `provider_code` é sanitizado e separado do código canônico.
4. `retryable` só é verdadeiro quando repetir for seguro e útil.
5. `Retry-After` acompanha `429`/`503` quando houver uma janela confiável.
6. Validação de payload usa detalhes por campo; autorização ocorre antes da validação sensível.
7. Falha durante Operation vai em `Operation.error`; falha que impede iniciar fica na resposta imediata.

## 8. AIP-194 aplicado a Meta Cloud e Evolution

O código atual já faz uma distinção importante com `ProviderError.retryable` e circuit breaker. O próximo passo é formalizar uma matriz:

| Condição | HTTP/código Mago | Retry automático | Ação |
|---|---|---:|---|
| Timeout de rede antes de confirmação | `UNAVAILABLE` | Sim, com idempotência | Backoff e reconciliação |
| 5xx do provider | `UNAVAILABLE` | Sim, limitado | Circuit breaker |
| 429/quota | `RESOURCE_EXHAUSTED` | Não cego | Respeitar Retry-After/quota |
| Payload inválido | `INVALID_ARGUMENT` | Não | Corrigir request |
| Token/credencial inválida | `UNAUTHENTICATED`/`FAILED_PRECONDITION` | Não | Reconfigurar integração |
| Canal desconectado | `FAILED_PRECONDITION` | Não até reconectar | Atualizar estado do canal |
| Provider rejeita destinatário | `FAILED_PRECONDITION` ou `INVALID_ARGUMENT` | Não | Expor motivo sanitizado |
| Resposta inválida do provider | `INTERNAL`/`UPSTREAM_INVALID_RESPONSE` | Não cego; reconciliar | Alertar e isolar |
| Circuit breaker aberto | `UNAVAILABLE` | Não no request atual | Retornar Retry-After |

Para mensagens, o consumidor deve receber aceitação da Operation quando o Mago assumiu a tarefa, não uma promessa falsa de entrega. `sent`, `delivered`, `read` e `failed` continuam sendo estados de mensagem derivados de webhooks/status do provider.

## 9. AIP-152 aplicado a Jobs

Jobs entram depois de Operation, porque o Mago ainda não tem um catálogo de execuções públicas. A ordem recomendada é:

1. `FlowJob` para flow configurável e repetível.
2. `CampaignJob` para campanha opt-in com limites, janela, audience snapshot e cancelamento.
3. `ImportJob`/`ExportJob` para arquivos e histórico.
4. Execuções subordinadas, por exemplo `jobs/{job_id}/executions/{execution_id}`.

Cada Job deve ter `Get/List/Create/Update/Delete` e um método `Run` via POST com `:run`, retornando Operation. A execução deve guardar contagens agregadas e falhas parciais; nunca armazenar conteúdo sensível além do necessário para auditoria e reconciliação.

## 10. AIP-203 e OpenAPI

Para cada novo request/response, o Mago deve declarar:

| Campo | Comportamento |
|---|---|
| `operation_id`, `name`, `created_time`, `complete_time` | output-only/identificador |
| `project_id`, `kind`, `request_id`/`Idempotency-Key` | required quando aplicável |
| `metadata`, `response`, `error` | output-only e mutuamente condicionais |
| `expire_time` | output-only |
| `provider`, `provider_flavor` | required na criação de canal quando o cliente escolhe provider |
| token, secret, API key | write-only/one-time; jamais em GET/list |
| filtros e page size | optional com limites documentados |

Os endpoints atuais permanecem com seus nomes e campos históricos. A melhoria começa nos novos schemas Pydantic e nos `response_model` das Operations; depois, os schemas públicos antigos recebem exemplos, `readOnly`/`writeOnly`, constraints e depreciações sem renomear campos de produção.

## 11. AIP-211 e isolamento multi-tenant

A autorização deve ser a primeira decisão de cada Operation. `GET /v1/operations/{id}` não pode consultar o registro global e só depois verificar projeto. O caminho seguro é resolver a API key, tenant e projeto permitidos, e somente então carregar a Operation com predicados completos.

Owner wildcard é uma capacidade administrativa explícita da conta owner e não deve vazar para Service API Keys. Uma chave customer-scoped só vê Operations do seu projeto. O endpoint de listagem deve filtrar por projeto no SQL, paginar e retornar `items` sem recurso de outro tenant. Uma chave com UUID malformado ou recurso inexistente não deve receber detalhes diferentes que permitam enumeração.

Webhooks de provider não possuem a mesma identidade de usuário: devem usar assinatura, instance/resource binding, deduplicação e evento persistente. Não devem aceitar `operation_id` arbitrário vindo do payload.

## 12. Plano de execução que acelera o produto

### P0 — contrato sem quebrar clientes

Adicionar Operation persistente, endpoints Get/List/Delete, envelope de erro ampliado e testes de cross-tenant. Não alterar o retorno padrão de `/v1/messages`.

### P1 — primeira operação externa

Aplicar modo assíncrono opt-in a envio de mensagem ou importação. Persistir aceite antes do provider, worker com backoff, reconciliation e webhook/status final. O cliente deixa de ficar bloqueado por timeout e ganha uma interface uniforme.

### P2 — operações Evolution

Fazer criação/reconnect/replay de alto custo retornarem Operation quando necessário; manter QR como estado exposto do channel. Adicionar `Retry-After`, progress, expires e estado terminal.

### P3 — Jobs vendáveis

Adicionar FlowJob/CampaignJob com `Run`, execuções e cancelamento cooperativo. Somente depois de operação, idempotência e reconciliação estarem comprovadas.

### P4 — SDKs e documentação

Gerar exemplos cURL/TypeScript/Python, helper de polling, tratamento de `Retry-After`, idempotency helper, webhooks assinados e matriz de erros. A documentação vira produto, não apenas referência de endpoint.

## 13. O que não fazer

Não copiar os protos Google para cada endpoint, não transformar tudo em gRPC, não criar um `/jobs` genérico sem estado real, não repetir envio externo apenas porque houve timeout, não expor token de Evolution em Operation, não renomear `created_at` em massa, não retornar 202 para clientes que esperam 201 sem negociação e não tratar Evolution como Meta oficial.

## 14. Critérios de aceite

Uma adoção mínima só deve ser considerada pronta quando:

- uma chamada repetida com a mesma chave e body retorna a mesma Operation;
- a mesma chave com body diferente retorna conflito;
- uma API key de projeto A não lê Operation de projeto B;
- autorização acontece antes de buscar ou detalhar o recurso;
- uma falha transitória usa backoff e não duplica efeito externo;
- uma falha permanente não entra em retry infinito;
- Operation concluída contém exatamente `response` ou `error`;
- metadata mostra estado/progresso/timestamps sem segredo;
- Operation expira e a política é documentada;
- cancelamento não promete interromper efeito que já foi enviado;
- o endpoint síncrono atual continua passando seus testes de compatibilidade;
- OpenAPI expõe required/readOnly/writeOnly e exemplos;
- Meta Cloud e Evolution permanecem adapters e semânticas separados.

## 15. Recomendação final

O AIP-151 não é um selo para colocar no README; é uma disciplina para transformar o Mago de uma coleção de endpoints e workers em uma plataforma previsível. A aplicação que mais acelera a venda e reduz suporte é: **Operation persistente + idempotência unificada + erro estruturado + polling simples + reconciliação segura**. Isso resolve a ansiedade do cliente diante de timeout, evita mensagens duplicadas, dá visibilidade para a equipe e prepara o terreno para campanhas e flows sem uma segunda arquitetura.

A primeira implementação deve ser pequena, aditiva e observável. Depois de provar uma operação ponta a ponta no canário, o mesmo contrato pode ser reutilizado em Meta Cloud e Evolution sem misturar os providers.

## Referências

[1]: https://google.aip.dev/151 "AIP-151: Long-running operations"
[2]: https://google.aip.dev/152 "AIP-152: Jobs"
[3]: https://google.aip.dev/155 "AIP-155: Request identification"
[4]: https://google.aip.dev/193 "AIP-193: Errors"
[5]: https://google.aip.dev/194 "AIP-194: Automatic retry configuration"
[6]: https://google.aip.dev/203 "AIP-203: Field behavior documentation"
[7]: https://google.aip.dev/211 "AIP-211: Authorization checks"
[8]: https://google.aip.dev/136 "AIP-136: Custom methods"
[9]: https://google.aip.dev/142 "AIP-142: Time and duration"
[10]: https://google.aip.dev/180 "AIP-180: Backwards compatibility"
