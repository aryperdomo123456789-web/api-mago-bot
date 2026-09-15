# API Mago Bot — Contrato P0 de Operations, Idempotência e Erros

Este documento descreve a primeira camada operacional da API Mago Bot para processamento persistente. A implementação segue os princípios do [AIP-151](https://google.aip.dev/151), do [AIP-152](https://google.aip.dev/152), do [AIP-155](https://google.aip.dev/155), do [AIP-193](https://google.aip.dev/193) e do [AIP-194](https://google.aip.dev/194), adaptados ao contrato REST/JSON multi-tenant do produto.

## Objetivo

Uma operação representa o acompanhamento persistente de uma mutação que pode ultrapassar o tempo de uma conexão HTTP, sofrer retry ou precisar ser reconciliada com o provider. A Operation é vinculada a um tenant e a um projeto e nunca expõe IDs internos, credenciais, tokens, payloads secretos ou stack traces.

A primeira entrega é aditiva. Os endpoints existentes continuam funcionando, inclusive o `POST /v1/messages` síncrono. Quando uma mensagem é aceita, a resposta também inclui a Operation correspondente, permitindo consultar o resultado mesmo que o cliente perca a conexão depois do aceite.

## Endpoints

| Método | Endpoint | Escopo mínimo | Finalidade |
|---|---|---|---|
| `GET` | `/v1/operations?project_id={public_project_uuid}` | `operations:read` | Lista Operations do projeto |
| `GET` | `/v1/operations/{operation_id}?project_id={public_project_uuid}` | `operations:read` | Consulta uma Operation |
| `DELETE` | `/v1/operations/{operation_id}?project_id={public_project_uuid}` | `operations:write` | Marca uma Operation como expirada/descartada |
| `POST` | `/v1/operations/{operation_id}:cancel?project_id={public_project_uuid}` | `operations:write` | Solicita cancelamento cooperativo |

Todas as chamadas exigem uma API key de serviço válida, são filtradas por tenant e projeto e carregam `X-Request-Id`/trace quando fornecidos pelo cliente. O identificador retornado é um UUID público.

## Estados

| Estado | Significado | `done` |
|---|---|---:|
| `queued` | Aceita e aguardando execução | não |
| `running` | Execução iniciada | não |
| `cancel_requested` | Cancelamento solicitado a um executor cooperativo | não |
| `succeeded` | Executada com resultado persistido | sim |
| `failed` | Terminou com erro persistido | sim |
| `cancelled` | Cancelada antes da execução | sim |
| `aborted` | Interrompida sem conclusão | sim |
| `expired` | Retenção ou descarte concluído | sim |

O cliente não deve inferir entrega de WhatsApp somente pelo estado da Operation. Para mensagens, `sent`, `delivered`, `read` e `failed` continuam sendo estados próprios da mensagem e dos eventos do provider.

## Exemplo de resposta

```json
{
  "name": "operations/8ce0c8c6-0b7d-4cf2-b8e4-07ad4e13d2cd",
  "id": "8ce0c8c6-0b7d-4cf2-b8e4-07ad4e13d2cd",
  "organization_id": "3e3f0a8b-2e4f-41c4-ae98-1d1d5c1e6e84",
  "project_id": "7b3290c4-7131-490f-8710-18b7ec353bfd",
  "kind": "message.send",
  "status": "succeeded",
  "done": true,
  "metadata": {
    "state": "succeeded",
    "attempt": 1,
    "provider": "evolution"
  },
  "response": {
    "message": {
      "id": "a1e79f2f-1dc7-4b95-ae23-e6d3acdbd450",
      "status": "sent"
    }
  },
  "error": null,
  "attempt_count": 1,
  "created_time": "2026-08-27T20:00:00Z",
  "start_time": "2026-08-27T20:00:01Z",
  "update_time": "2026-08-27T20:00:02Z",
  "complete_time": "2026-08-27T20:00:02Z",
  "expire_time": "2026-09-26T20:00:00Z"
}
```

## Idempotência

Toda mutação que cria efeito externo deve receber um `X-Idempotency-Key` com 16 a 160 caracteres. A chave é combinada com tenant, projeto, tipo de operação e endpoint lógico. O payload é normalizado em JSON ordenado e recebe hash SHA-256 antes de ser persistido.

A mesma chave com o mesmo payload retorna replay seguro. A mesma chave com payload diferente retorna `409` e razão `IDEMPOTENCY_KEY_REUSED`. A chave não deve ser reutilizada entre ações diferentes. O cliente deve repetir a chave original apenas quando estiver tentando obter o mesmo resultado, não para iniciar uma nova mensagem.

## Envelope de erro

Respostas de erro possuem `error` e preservam `detail` por compatibilidade temporária:

```json
{
  "error": {
    "code": "provider_unavailable",
    "message": "O provider não concluiu a operação.",
    "status": "UNAVAILABLE",
    "reason": "PROVIDER_UNAVAILABLE",
    "domain": "api.mago-bot.com/providers/evolution",
    "retryable": true,
    "retry_after_seconds": 30,
    "request_id": "req_01J8MAGO123",
    "details": []
  },
  "detail": {
    "code": "provider_unavailable",
    "message": "provider unavailable"
  }
}
```

A API envia `Retry-After` quando há janela recomendada. Erros de validação não são retryable. Indisponibilidade transitória, circuit breaker e limites temporários podem ser retryable. Credencial inválida, payload inválido, quota excedida, canal desconectado e destinatário rejeitado não devem sofrer retry cego.

## Retenção e autorização

Operations expiram por padrão após 30 dias, com limite de retenção controlado pelo servidor. Cada leitura consulta simultaneamente `organization_id`/tenant e `project_id`; um UUID existente em outro tenant retorna `404`, sem revelar a existência do recurso. A autorização é aplicada antes da exposição do conteúdo.

## Compatibilidade

A entrega não altera o significado dos endpoints antigos. A camada pública adiciona o recurso de Operations e inclui a Operation no retorno do envio de mensagem. O provider Meta Cloud continua isolado como oficial, e Evolution continua isolado como camada de compatibilidade. Nenhum segredo de provider é serializado no recurso público.

## Critérios de aceite P0

A entrega só é considerada pronta quando os testes comprovam hash determinístico, replay, conflito por payload diferente, UUID público, estados terminais, envelope com `reason`/`domain`/`retryable`/`Retry-After`, ausência de stack trace, presença no OpenAPI, acesso customer somente em `app.mago-bot.com` e `404` em `evo-api.mago-bot.com`.
