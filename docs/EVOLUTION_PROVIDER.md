# Evolution / Compatibilidade — Mago Bot

**Status:** provider de compatibilidade em produção controlada; laboratório autenticado pendente de MFA owner
**Versão do contrato Mago:** 1.0
**Última revisão:** 2026-08-26
**Autor:** Manus AI

## Posicionamento

A camada Evolution conecta sessões WhatsApp Web por meio do provider Evolution. Ela é uma alternativa operacional para pilotos, atendimento opt-in e notificações legítimas. **Não é a WhatsApp Business Platform oficial da Meta** e não deve ser comercializada como equivalente regulatório ou de SLA à Meta Cloud API.

O Mago Bot mantém um contrato unificado de projetos, resources, API keys, quotas, idempotência, conversas, webhooks, auditoria e tracing. A instância Evolution fica encapsulada atrás do `EvolutionAdapter` e do `EvolutionManagementAdapter`; a chave global do provider e o token da instância permanecem server-side e cifrados quando persistidos.

> O objetivo de paridade é de experiência operacional: lifecycle, estado confiável, mídia, observabilidade e documentação. O transporte, a política de qualidade e as garantias da Meta continuam diferentes.

## Arquitetura

A conta `owner` é um operador wildcard administrativo: ela pode operar recursos customer-scoped de tenants ativos e, adicionalmente, provisionar tenant, membership, assinatura, projeto e fila inicial. Essa capacidade não é um bypass anônimo: usa a mesma sessão revogável, permanece restrita à Operations Console e exige MFA habilitado para provisionamento. Usuários tenant continuam limitados ao próprio membership e projeto.


```text
Cliente / SDK / API key
          |
          v
Mago Bot Control Plane
  tenant • projeto • quota • auditoria • inbox • webhooks
          |
   Evolution Management Adapter
      /                    \
Evolution API v2       Evolution Go
      \                    /
       Unified Message / Conversation Core
```

A instalação produtiva atual usa Evolution API v2. O adapter também possui flavor `evolution_go` para a API documentada pela Evolution Foundation. O flavor não deve ser alternado em uma instância existente sem validar os endpoints, o modelo de autenticação e o contrato de payload do provider alvo.

## Lifecycle gerenciado

A Operations Console expõe a gestão em **Evolution / Compatibilidade**, na superfície central `evo-api.mago-bot.com`. O cliente de portal nunca recebe a chave global do provider.

| Operação | Endpoint Mago | Efeito |
|---|---|---|
| Listar | `GET /v1/ops/evolution/instances` | Lista instâncias não deletadas sem token |
| Criar | `POST /v1/ops/evolution/instances` | Cria resource, gera token, cifra segredo e provisiona no provider |
| Conectar | `POST /v1/ops/evolution/instances/{id}/connect` | Inicia conexão e configura callback quando disponível |
| QR | `GET /v1/ops/evolution/instances/{id}/qr` | Retorna QR temporário somente para operador autorizado |
| Pairing | `POST /v1/ops/evolution/instances/{id}/pair` | Disponível para o flavor Evolution Go |
| Health | `POST /v1/ops/evolution/instances/{id}/status` | Consulta o provider e normaliza estado |
| Reconectar | `POST /v1/ops/evolution/instances/{id}/reconnect` | Solicita reconexão no provider |
| Desconectar | `POST /v1/ops/evolution/instances/{id}/disconnect` | Desconecta sem apagar o resource |
| Logout | `POST /v1/ops/evolution/instances/{id}/logout` | Encerra a sessão do provider |
| Excluir | `DELETE /v1/ops/evolution/instances/{id}` | Exclui no provider e faz tombstone lógico no Mago |

As mutações exigem owner, `platform_superadmin` ou `platform_operator`, são auditadas e não retornam `instance_token`, `apikey`, senha ou segredo de webhook. O provisionamento owner-only de tenant/projeto exige MFA habilitado e é transacional. Suporte possui leitura operacional limitada; `platform_partner` não acessa a central.

## Máquina de estados

As instâncias usam estados explícitos para que a interface não confunda “chave configurada” com “WhatsApp conectado”.

| Estado | Significado |
|---|---|
| `provisioning` | Registro local criado e chamada de provisionamento pendente |
| `created` | Instância criada no provider, ainda sem sessão conectada |
| `qr_pending` | QR disponível ou aguardando escaneamento |
| `pairing_pending` | Código de pareamento solicitado |
| `connected` | Último health/evento confirmou conexão |
| `syncing` | Provider informou sincronização/histórico |
| `disconnected` | Sessão caiu ou foi desconectada |
| `degraded` | Health falhou ou provider respondeu estado não confiável |
| `logged_out` | Logout executado |
| `suspended` | Resource bloqueado pela operação/tenant |
| `failed` | Provisionamento ou ação falhou de forma persistente |
| `deleted` | Tombstone local; não aparece em listagens normais |

O `evolution-health-worker` consulta instâncias vencidas em intervalos controlados, atualiza `last_status_check_at`, `last_connected_at`, `jid`, telefone sanitizado e erro limitado. O worker possui heartbeat e healthcheck Docker. O health worker **não reconecta automaticamente**: reconexão é uma ação auditada para evitar loops e comportamento inesperado no provider.

## Webhook normalizado

O endpoint gerenciado é:

```text
POST /v1/webhooks/evolution/{instance_uuid}/{endpoint_secret}
```

A URL completa só é montada em memória a partir do segredo cifrado. Ela não aparece em listagens. O endpoint valida o UUID, compara o segredo em tempo constante, impõe limite de payload, sanitiza `instanceToken`, `apikey`, `password` e `secret`, deduplica por instância e evento e registra `EvolutionInstanceEvent`.

Eventos de conexão atualizam a máquina de estados. Eventos de mensagem são normalizados no Conversation Core e geram delivery para as subscriptions downstream do projeto. O webhook responde rápido; processamento de entrega, retry e backoff pertencem ao worker de webhooks.

O callback interno é preferido quando `EVOLUTION_WEBHOOK_PUBLIC_URL` está configurado. No proxy central, `/v1/webhooks/evolution/` vai para o Mago em `4349`; não cai no fallback público da Evolution em `4348`.

## Mensagens e mídia

O contrato público do Mago continua:

```http
POST /v1/projects/{project_id}/messages
X-API-Key: mb_live_...
X-Idempotency-Key: pedido-2026-0001
Content-Type: application/json
```

Texto:

```json
{
  "to": "5511999999999",
  "type": "text",
  "text": {"body": "Mensagem opt-in"}
}
```

Mídia usa URL HTTPS ou base64 validado dentro de `media`, com tipo limitado a `image`, `video`, `audio`, `document` ou `sticker`. O adapter traduz o payload para Evolution API v2 (`/message/sendMedia/{instance}`) ou Evolution Go (`/send/media`). Para arquivos grandes, a evolução recomendada é mover o upload para S3/MinIO com URL assinada e TTL; não gravar base64 no banco.

A camada não deve prometer templates aprovados pela Meta. Mensagens comerciais, disparos frios e automação sem opt-in são proibidos no posicionamento do produto.

## Configuração server-side

Variáveis principais no serviço:

```dotenv
EVOLUTION_INTERNAL_URL=http://evolution-api:8080
EVOLUTION_API_KEY=<secret server-side>
EVOLUTION_PROVIDER_FLAVOR=evolution_api
EVOLUTION_HTTP_TIMEOUT=20
EVOLUTION_WEBHOOK_PUBLIC_URL=https://evo-api.mago-bot.com
EVOLUTION_QR_TTL_SECONDS=60
EVOLUTION_HEALTH_POLL_SECONDS=30
EVOLUTION_HEALTH_CHECK_INTERVAL_SECONDS=45
EVOLUTION_HEALTH_WORKER_HEARTBEAT=/tmp/mago_evolution_health_worker_heartbeat
```

O arquivo `.env` real nunca deve entrar no GitHub ou em relatório. O `service.env.example` contém placeholders e deve ser usado somente como referência. Produção deve configurar `EVOLUTION_WEBHOOK_PUBLIC_URL` depois de confirmar o proxy central e o DNS; o canário deve apontar para uma URL isolada ou permanecer sem callback para não mandar eventos de teste à produção.

## Observabilidade e segurança

Cada mutação de lifecycle gera `AuditEvent`. Erros de rede e HTTP 5xx/429 são classificados como temporários; respostas 4xx de payload ou autorização não entram em retry cego. O circuito do provider e o usage ledger continuam pertencendo ao Mago.

O Manager público permanece bloqueado. A GLOBAL_API_KEY não deve aparecer em HTML, OpenAPI, logs, webhook downstream ou resposta de erro. QR e pairing são segredos operacionais temporários e só podem ser mostrados a operador autorizado. A URL do webhook gerenciado contém um segredo de endpoint e nunca deve ser copiada para observabilidade ou tela do tenant.

## Limites honestos

| Capability | Evolution | Meta Cloud |
|---|---|---|
| QR/pairing de sessão | Sim, conforme o flavor/provider | Não é o fluxo principal |
| WABA e Phone Number ID | Não | Sim |
| Templates aprovados | Não como garantia do provider | Sim |
| Qualidade e políticas oficiais | Não | Sim |
| Lifecycle operacional | Encapsulado pelo Mago | Encapsulado pelo Mago |
| Mídia e interativos | Conforme endpoint/flavor | Conforme Cloud API |
| SLA e estabilidade | Dependem da sessão/provider | Dependem da Meta Cloud |

A Evolution deve ser vendida como **compatibilidade**. A Meta Cloud deve ser vendida como **camada oficial**. A API do Mago permanece igual para o cliente, mas o plano, limite e aviso de risco devem refletir o provider escolhido.

## Rollout e critérios de aceite

Antes de promover uma mudança Evolution, o canário deve ter a migration aplicada, app e health worker `healthy`, OpenAPI contendo lifecycle e webhook, `GET /v1/ops/evolution/instances` retornando `401` sem sessão no host operacional, webhook inválido retornando `404`, e nenhum traceback nos logs recentes. Um teste autenticado de criação só pode usar uma instância de teste que não seja o número de produção.

A promoção deve criar backup dos arquivos e banco antes da migration, reconstruir somente app/worker Evolution, testar `nginx -t` se o callback público for alterado e validar novamente as superfícies `evo-api` e `app`. Rollback remove o health worker se necessário, restaura os arquivos do backup e mantém a migration compatível; não se deve apagar tabelas em produção como primeira reação.

## References

[1]: https://docs.evolutionfoundation.com.br/evolution-go "Evolution Go — documentação oficial"

[2]: https://github.com/evolution-foundation/evolution-go "Evolution Go — repositório oficial"

[3]: https://developers.facebook.com/docs/whatsapp/cloud-api "Meta WhatsApp Cloud API — documentação oficial"
