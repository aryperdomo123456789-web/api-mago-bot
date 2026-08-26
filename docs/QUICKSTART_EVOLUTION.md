# Quickstart — Mago Bot + Evolution

Este quickstart usa somente a API pública do Mago. A chave `EVOLUTION_API_KEY` e o token da instância nunca entram no cliente. Evolution é provider de compatibilidade; para produção crítica, use Meta Cloud conforme o plano e o contrato.

## Pré-requisitos

O operador cria uma instância em **Evolution / Compatibilidade** na Operations Console, conecta por QR ou pairing e aguarda o estado `connected`. O resource precisa estar ativo no projeto e a API key deve ter somente os scopes necessários para envio e leitura.

## Enviar texto com cURL

```bash
curl --fail-with-body --request POST \
  'https://app.mago-bot.com/v1/projects/PROJECT_ID/messages' \
  --header 'X-API-Key: mb_live_REDACTED' \
  --header 'X-Idempotency-Key: order-2026-000001' \
  --header 'Content-Type: application/json' \
  --data '{"to":"5511999999999","type":"text","text":{"body":"Mensagem opt-in"}}'
```

O `X-Idempotency-Key` precisa ser único por operação. Em timeout, repita a mesma requisição com a mesma chave; não gere uma nova mensagem por tentativa.

## Enviar mídia

```bash
curl --fail-with-body --request POST \
  'https://app.mago-bot.com/v1/projects/PROJECT_ID/messages' \
  --header 'X-API-Key: mb_live_REDACTED' \
  --header 'X-Idempotency-Key: order-2026-000002' \
  --header 'Content-Type: application/json' \
  --data '{"to":"5511999999999","type":"image","media":{"type":"image","url":"https://cdn.example.com/catalogo.png","caption":"Imagem solicitada"}}'
```

A URL de mídia deve ser HTTPS, pública para o provider, sem credenciais embutidas e dentro do limite contratado. Para arquivos grandes, use S3/MinIO com URL assinada e TTL; não grave base64 permanente no banco.

## Python

```python
import os
import uuid
import requests

BASE_URL = os.environ.get("MAGO_API_BASE_URL", "https://app.mago-bot.com")
PROJECT_ID = os.environ["MAGO_PROJECT_ID"]
API_KEY = os.environ["MAGO_API_KEY"]

response = requests.post(
    f"{BASE_URL}/v1/projects/{PROJECT_ID}/messages",
    headers={
        "X-API-Key": API_KEY,
        "X-Idempotency-Key": f"python-{uuid.uuid4()}",
    },
    json={
        "to": "5511999999999",
        "type": "text",
        "text": {"body": "Mensagem opt-in"},
    },
    timeout=20,
)
response.raise_for_status()
print(response.json())
```

## TypeScript

```typescript
const baseUrl = process.env.MAGO_API_BASE_URL ?? "https://app.mago-bot.com";
const projectId = process.env.MAGO_PROJECT_ID!;
const apiKey = process.env.MAGO_API_KEY!;

const response = await fetch(`${baseUrl}/v1/projects/${projectId}/messages`, {
  method: "POST",
  headers: {
    "X-API-Key": apiKey,
    "X-Idempotency-Key": `typescript-${crypto.randomUUID()}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    to: "5511999999999",
    type: "text",
    text: { body: "Mensagem opt-in" },
  }),
});

if (!response.ok) throw new Error(`Mago HTTP ${response.status}`);
console.log(await response.json());
```

## Webhooks

Cadastre o endpoint downstream do projeto na Operations Console. O Mago entrega eventos assinados com `X-Mago-Signature`, `X-Mago-Delivery-Id` e retry classificado. Responda 2xx rapidamente e processe o conteúdo de forma assíncrona. Valide assinatura antes de interpretar dados e trate `delivery_id` como idempotência.

## Diagnóstico

Consulte o status do resource na central. `connected` indica que o último health/evento confirmou sessão; `degraded` exige inspeção do erro; `qr_pending` exige novo pareamento; `logged_out` não deve ser reconectado automaticamente sem ação do operador. Não use a chave Evolution diretamente nem exponha o Manager.

## Limites honestos

Este contrato não fornece WABA, templates aprovados, qualidade ou SLA da Meta. Use Evolution apenas para opt-in, suporte, notificações legítimas e pilotos dentro das quotas do plano. O provider pode cair ou exigir novo pareamento; o Mago registra esse estado e protege as mensagens contra duplicação.

## References

[1]: https://docs.evolutionfoundation.com.br/evolution-go "Evolution Go — documentação oficial"

[2]: https://developers.facebook.com/docs/whatsapp/cloud-api "Meta WhatsApp Cloud API — documentação oficial"
