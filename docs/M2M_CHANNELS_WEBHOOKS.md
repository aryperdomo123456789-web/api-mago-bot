# API Mago Bot — Canais M2M e Webhooks Downstream

Este documento define a superfície de integração máquina-a-máquina da **API Mago Bot**. Ela é consumida por sistemas do cliente com `X-API-Key` e não depende de sessão de cookies do portal. O projeto da chave determina o tenant e o escopo de todos os recursos.

## 1. Autenticação e isolamento

As rotas M2M exigem o header `X-API-Key`. Cookies de sessão e o login da Operations Console não substituem esse header. A chave deve ser emitida para o projeto correto e conter, no mínimo, `channels:read` para leitura, `channels:write` para lifecycle, `webhooks:read` para consulta e `webhooks:write` para criação de subscriptions.

A API resolve o `project_uuid` público dentro do tenant vinculado à chave. Uma chave de outro projeto recebe `404` e não revela se o recurso existe. IDs internos do banco não fazem parte das respostas M2M.

## 2. Canais Evolution

| Método | Endpoint | Scope | Idempotência |
|---|---|---|---|
| `GET` | `/v1/projects/{project_uuid}/channels` | `channels:read` | não necessária |
| `POST` | `/v1/projects/{project_uuid}/channels` | `channels:write` | `X-Idempotency-Key` obrigatório |
| `GET` | `/v1/channels/{channel_uuid}` | `channels:read` | não necessária |
| `POST` | `/v1/channels/{channel_uuid}/connect` | `channels:write` | `X-Idempotency-Key` obrigatório |
| `GET` | `/v1/channels/{channel_uuid}/status` | `channels:read` ou `channels:write` | não necessária |
| `GET` | `/v1/channels/{channel_uuid}/qr` | `channels:write` | `X-Idempotency-Key` obrigatório |
| `POST` | `/v1/channels/{channel_uuid}/pair` | `channels:write` | `X-Idempotency-Key` obrigatório |
| `POST` | `/v1/channels/{channel_uuid}/reconnect` | `channels:write` | `X-Idempotency-Key` obrigatório |
| `POST` | `/v1/channels/{channel_uuid}/disconnect` | `channels:write` | `X-Idempotency-Key` obrigatório |

O provider público é declarado como `evolution` e o `provider_flavor` pode ser `evolution_api` ou `evolution_go`. A API não apresenta Evolution como Meta Cloud oficial. Meta Cloud permanece em adapter, contrato e credenciais separados.

Uma criação usa payload semelhante a:

```json
{
  "display_name": "laboratorio-cliente-01",
  "provider": "evolution",
  "provider_flavor": "evolution_api",
  "events": [
    "message.inbound",
    "message.status",
    "connection.updated",
    "qrcode.updated"
  ]
}
```

O header `X-Idempotency-Key` deve ter entre 16 e 160 caracteres. A chave é vinculada ao tenant, projeto, operação e hash canônico do payload. Repetir a mesma requisição devolve replay do resultado; reutilizá-la com outro payload retorna `409`.

As respostas mostram estado, capacidade, phone/JID sanitizados, UUIDs públicos e uma operação correlacionada. Nunca mostram `instance_token`, `apikey`, senha, secret do provider, QR ou pairing code no bloco genérico `provider`. QR e pairing só aparecem nos endpoints que os solicitam explicitamente e são artefatos efêmeros de conexão.

## 3. Subscriptions downstream

| Método | Endpoint | Scope | Idempotência |
|---|---|---|---|
| `GET` | `/v1/projects/{project_uuid}/webhooks` | `webhooks:read` ou `webhooks:write` | não necessária |
| `POST` | `/v1/projects/{project_uuid}/webhooks` | `webhooks:write` | `X-Idempotency-Key` obrigatório |
| `GET` | `/v1/webhooks/events` | `webhooks:read` ou `webhooks:write` | não necessária |

O endpoint precisa ser HTTPS público, não pode apontar para loopback, `.local` ou faixa privada e é validado contra SSRF antes de ser persistido. A criação retorna o `secret` downstream uma única vez. Ele não é devolvido por listagem nem por consulta posterior.

Eventos canônicos permitidos:

```text
message.inbound
message.status
connection.updated
qrcode.updated
```

O sistema aceita aliases históricos de subscriptions, como `messages`, `statuses` e `account`, para compatibilidade. Eventos novos são armazenados e entregues com o tipo canônico.

## 4. Payload e assinatura

Cada entrega contém JSON compacto com o identificador estável do evento, tipo canônico, provider e dados sanitizados:

```json
{
  "id": "event-uuid",
  "type": "message.inbound",
  "provider": "evolution",
  "created_at": "2026-08-27T22:00:00+00:00",
  "data": {}
}
```

O header `X-Mago-Signature` tem o formato `sha256={hex}` e é calculado sobre os bytes exatos do corpo HTTP usando HMAC-SHA256. A entrega também inclui `X-Mago-Event-ID`, `X-Mago-Delivery-ID` e `X-Mago-Event-Type`.

Exemplo de verificação:

```python
import hashlib
import hmac

expected = hmac.new(
    WEBHOOK_SECRET.encode("utf-8"),
    raw_request_body,
    hashlib.sha256,
).hexdigest()
valid = hmac.compare_digest(
    request.headers["X-Mago-Signature"],
    f"sha256={expected}",
)
```

O consumidor deve validar a assinatura sobre o corpo bruto, rejeitar replay conforme sua política de `X-Mago-Event-ID`/`X-Mago-Delivery-ID` e responder rapidamente com `2xx`. O worker aplica timeout, não segue redirect, controla SSRF e usa retry exponencial até o limite configurado; respostas não-2xx viram retry ou dead-letter conforme a contagem de tentativas.

## 5. Operações e erros

Mutations M2M criam uma `Operation` persistente com `operations/{uuid}`, estado `queued`, `running`, `succeeded`, `failed`, `cancelled`, `aborted` ou `expired`, metadata, resposta, erro e expiração. O cliente pode consultar a operação pela superfície pública de Operations usando uma API key do mesmo projeto.

Erros seguem o envelope estruturado da API Mago Bot. O campo `detail` legado continua presente quando aplicável, mas clientes novos devem usar:

```json
{
  "error": {
    "code": "provider_timeout",
    "message": "Evolution management request timed out",
    "status": "UNAVAILABLE",
    "reason": "PROVIDER_UNAVAILABLE",
    "domain": "api.mago-bot.com/providers/evolution",
    "retryable": true,
    "retry_after_seconds": 30,
    "request_id": "req-uuid",
    "details": []
  }
}
```

## 6. Limites honestos

A superfície M2M está pronta para integração controlada, mas a criação de canal ainda depende do provider Evolution configurado no runtime. Pairing code não é garantido no flavor `evolution_api`; nesse caso a API responde `422` com `unsupported_operation` e o cliente deve usar QR. O cancelamento de Operation é cooperativo e não desfaz uma chamada externa já aceita pelo provider.

A primeira versão de subscriptions cobre criação e listagem; rotação/revogação administrativa dedicada deve ser adicionada antes de oferecer gerenciamento completo de ciclo de vida de secrets a clientes enterprise. Enquanto isso, trate o secret retornado na criação como credencial de alta sensibilidade e armazene-o em cofre próprio.
