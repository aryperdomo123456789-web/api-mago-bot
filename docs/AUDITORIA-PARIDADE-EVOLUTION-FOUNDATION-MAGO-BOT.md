# Auditoria de paridade Evolution Foundation e plano Mago Bot

## Resumo em linguagem simples

Imagine que o WhatsApp seja uma cidade.

- Uma **instância** é uma casa conectada ao WhatsApp.
- Um **QR Code** é a chave usada para abrir a porta da casa.
- Uma **mensagem** é uma carta enviada ou recebida.
- Um **webhook** é um carteiro que avisa quando algo aconteceu.
- Um **provider** é o caminho usado para chegar à cidade.
- O **Mago Bot** é o administrador que organiza casas, moradores, chaves, limites, carteiros e registros.

A Evolution Foundation oferece muito mais do que enviar texto: lifecycle de instâncias, QR e pairing, mensagens, mídia, contatos, chats, grupos, presença, eventos, webhooks, filas, armazenamento, integrações com automação e conexão oficial Meta Cloud. A documentação oficial também marca alguns recursos como experimentais, em homologação ou descontinuados. Portanto, o objetivo correto do Mago Bot é oferecer uma experiência mais segura, simples e auditável, mantendo claramente separado o que é compatibilidade WhatsApp Web e o que é Meta Cloud oficial.

**Veredito:** a fundação do Mago Bot já possui control plane, isolamento, API keys, quotas, operações, canais Evolution, mensagens, webhooks, inbox e console operacional. Ainda não existe paridade comprovada com todo o catálogo da Evolution Foundation. Para alcançar uma paridade real, o trabalho deve ser dividido em capacidades testáveis e providers específicos.

## 1. Escopo e método

Esta auditoria compara:

1. o site público da Evolution Foundation;
2. o repositório oficial Evolution API;
3. a documentação oficial da Evolution API e Evolution Go;
4. o código e a documentação existentes no Mago Bot;
5. o que pode ser prometido, o que precisa de teste e o que deve permanecer explicitamente diferente.

O site institucional tem conteúdo público limitado quando acessado sem uma sessão visual completa. Por isso, as afirmações técnicas foram verificadas principalmente na documentação oficial e no repositório oficial, que descrevem endpoints, eventos, providers, integrações e configuração.

Uma capacidade só recebe o selo **pronta** quando possui:

- contrato de API;
- autenticação e autorização;
- persistência ou estado definido;
- tratamento de erro;
- auditoria e observabilidade;
- teste de sucesso;
- teste de falha e recuperação;
- documentação que alguém consegue seguir.

## 2. O que a Evolution Foundation apresenta

O repositório oficial descreve a Evolution API como uma API REST de integração com WhatsApp e mensageria multicanal, parte do ecossistema Evolution Foundation. Ele lista suporte a Baileys/WhatsApp Web, Meta Cloud API, integrações de chatbot, transportes de eventos, armazenamento S3/MinIO, PostgreSQL/MySQL, Redis e Docker.[1]

A arquitetura publicada é semelhante a:

```text
Aplicação do cliente
        |
        v
API de controle de mensagens
        |
  +-----+-----------+----------------+
  |                 |                |
WhatsApp Web    Meta Cloud      Integrações
Baileys         oficial         Typebot/CRM/IA
  |                 |                |
  +----------- Eventos -------------+
        |
 Webhook / fila / WebSocket
```

O Mago Bot deve usar uma arquitetura equivalente em conceito, mas com uma fronteira mais rigorosa:

```text
Cliente / SDK / API key
        |
        v
Mago Bot Control Plane
tenant • projeto • quota • operação • auditoria
        |
   Adapter de provider
    /              \
Evolution Web    Meta Cloud
compatibilidade  oficial
        |
Conversation Core + Webhooks + Inbox
```

O cliente não deve receber a chave global do provider, o nome interno da instância, o token da sessão, o host interno ou segredo de webhook.

## 3. Catálogo completo de capacidades

### 3.1 Instâncias e conexão

| Capacidade | Evolution Foundation | Mago Bot | Decisão |
|---|---|---|---|
| Criar instância | Sim | Parcialmente existente | Expor criação por `channel_uuid`, não por nome interno |
| Excluir instância | Sim | Existente com tombstone | Manter exclusão auditada e idempotente |
| Conectar | Sim | Existente | Exigir operação, timeout e motivo |
| QR Code | Sim | Existente | QR temporário, operador autorizado e expiração explícita |
| Pairing code | Conforme provider | Flavor Evolution Go | Não prometer quando o provider não suportar |
| Status | Sim | Existente | Normalizar para máquina de estados Mago |
| Reconectar | Sim | Existente | Ação auditada; não reconectar em loop automaticamente |
| Logout | Sim | Existente | Diferenciar `logged_out` de `disconnected` |
| Telefone/JID | Sim | Persistido de forma sanitizada | Nunca exibir token ou payload bruto |
| Sincronização inicial | Sim | Parcial | Criar estado `syncing` e limite operacional |
| Sessão persistente | Sim | Volume/provider existente | Fazer backup e restore isolado antes de vender |

Na documentação oficial, a criação de instância aceita QR, integração, número, webhook e configurações de sessão. O retorno inclui estado e dados temporários de QR.[2] No Mago, esses dados precisam passar pelo control plane; o cliente recebe apenas o QR temporário ou uma operação consultável.

### 3.2 Mensagens

A documentação oficial lista texto, mídia, áudio narrado, localização, contato, reação, pré-visualização de link, resposta, menção, enquete, status, adesivo e listas em homologação. Botões aparecem como descontinuados na camada não-cloud.[3]

O Mago deve organizar essas capacidades em três níveis:

| Nível | Recursos | Regra |
|---|---|---|
| P0 | Texto, imagem, documento, áudio, vídeo, localização, contato, resposta e reação | Primeiro ciclo vendável |
| P1 | Menção, enquete, sticker, preview de link e mensagens de grupo | Depois do E2E básico |
| P2 | Status/histórias, listas e interativos provider-specific | Somente com capability discovery e testes por flavor |

Contrato Mago recomendado:

```json
{
  "to": "5511999999999",
  "type": "text",
  "text": {"body": "Mensagem com opt-in"},
  "reply_to": null,
  "mentions": []
}
```

Para mídia:

```json
{
  "to": "5511999999999",
  "type": "image",
  "media": {
    "url": "https://cdn.example.com/catalogo.png",
    "caption": "Imagem solicitada"
  }
}
```

Regras obrigatórias:

- HTTPS para URL externa;
- bloqueio de hosts privados e metadata endpoints;
- allowlist de MIME e tamanho;
- URL assinada e expiração para arquivos privados;
- nunca guardar base64 grande como caminho principal no banco;
- persistir `message_uuid`, `operation_uuid`, provider message ID e estado normalizado;
- idempotência por chave e payload;
- erro público sem token, senha ou cabeçalho sensível.

### 3.3 Contatos, chats e grupos

A Evolution Foundation documenta eventos de contatos, chats e grupos, além de criação e atualização de grupos.[4]

O Mago deve implementar uma camada de domínio, não simplesmente repassar o endpoint:

```text
CustomerProfile
  └── Identity / número
       └── Conversation / chat
            └── Message / evento
```

Capacidades planejadas:

- listar contatos;
- buscar contato por telefone/JID;
- atualizar perfil local;
- listar chats;
- arquivar, reabrir e marcar conversa;
- criar grupo;
- atualizar assunto, descrição e foto;
- listar participantes;
- adicionar, remover, promover e rebaixar participante;
- aplicar política de permissão por projeto;
- registrar toda mutação em auditoria.

O primeiro produto não deve liberar administração de grupos para qualquer API key. Essa área tem potencial de abuso e precisa de scopes separados, por exemplo `whatsapp:groups:read` e `whatsapp:groups:manage`.

### 3.4 Presença, status e chamadas

A API documenta presença como `available`, `unavailable`, `composing` e `recording`.[5] O Mago deve tratar presença como uma capability opcional e efêmera:

- não persistir presença como verdade permanente;
- aplicar TTL;
- limitar frequência;
- impedir loops de “digitando”;
- não anunciar suporte quando o provider não confirmar;
- separar chamada/voice events de mensagem comum.

Chamadas, status/histórias e eventos de presença devem ser P2. Eles não podem bloquear o primeiro piloto de texto, webhook e inbox.

### 3.5 Webhooks

Os eventos oficiais documentados incluem inicialização, QR, conexão, carga inicial de mensagens, mensagens recebidas, atualização e exclusão de mensagens, envio, contatos, presença, chats, grupos e atualização de token.[6]

Contrato interno Mago:

```text
provider event
  -> validação do canal
  -> deduplicação por provider_event_id
  -> normalização
  -> persistência do evento
  -> atualização de estado/message/conversation
  -> outbox downstream
  -> entrega assinada ao cliente
```

Contrato downstream mínimo:

- `X-Mago-Signature`;
- `X-Mago-Delivery-Id`;
- versão do evento;
- `occurred_at`;
- `project_uuid`;
- `channel_uuid`;
- `event_type`;
- `data` normalizado;
- nenhum segredo do provider.

O webhook de entrada deve responder rapidamente. O processamento pesado deve ocorrer no worker. Falha do endpoint cliente não pode fazer a Evolution reenviar indefinidamente sem controle do Mago.

O Mago precisa adicionar para paridade operacional:

- log de cada delivery;
- tentativa atual e próxima tentativa;
- backoff exponencial com limite;
- dead-letter queue;
- replay manual auditado;
- pausa automática de destino com muitas falhas;
- teste de assinatura inválida;
- teste de payload duplicado;
- teste de evento desconhecido.

### 3.6 Filas e transportes de eventos

A Evolution Foundation documenta webhook HTTP, WebSocket, RabbitMQ, Amazon SQS, NATS e outros transportes/integracões de eventos.[1][7]

O Mago não deve adicionar todos de uma vez. A ordem correta é:

1. outbox transacional interno;
2. worker de webhook HTTP;
3. replay e DLQ;
4. WebSocket/SSE para painel;
5. RabbitMQ/NATS para clientes enterprise;
6. SQS/Kafka/Pusher somente quando existir demanda e operação real.

Cada transporte precisa de um contrato comum. O evento não pode mudar dependendo de a entrega ter saído por HTTP, fila ou WebSocket.

### 3.7 Mídia e armazenamento

A documentação oficial lista armazenamento local e S3/MinIO.[1] O Mago deve escolher S3-compatible como padrão de produção:

- bucket privado por ambiente;
- prefixo por tenant/projeto/channel;
- URL assinada com TTL;
- limite de tamanho;
- validação de MIME real;
- limpeza de objetos órfãos;
- criptografia e lifecycle policy;
- nenhum segredo em URL permanente;
- auditoria de download quando o conteúdo for sensível.

O provider pode devolver mídia inline ou por URL. O Mago deve normalizar para `media_ref` e não prometer que o base64 estará sempre disponível.

### 3.8 Integrações

O ecossistema oficial lista Typebot, Chatwoot, OpenAI, Dify, N8N, Flowise e EvoAI, além de integrações de eventos e armazenamento.[1]

O Mago deve oferecer primeiro adaptadores seguros:

| Integração | Forma recomendada |
|---|---|
| Chatwoot | webhook e conector de conversa, com tenant isolado |
| Typebot/Dify/N8N | webhook/API key por projeto, sem chave global |
| OpenAI | adapter server-side opcional, com consentimento e orçamento |
| S3/MinIO | storage de mídia assinado |
| RabbitMQ/NATS | integração enterprise com namespace por tenant |
| Meta Cloud | adapter separado, com WABA, Phone Number ID e templates |

Não copiar integrações só para aumentar a lista. Cada integração precisa de ownership, rotação de segredo, retry, limites, auditoria e desativação.

## 4. Autenticação e isolamento

A Evolution API documenta `apikey` global ou token específico por instância.[1] Essa é uma autenticação de provider. Não deve ser a autenticação do cliente Mago.

No Mago:

- usuário usa sessão segura no portal;
- sistema usa API key limitada ao projeto para M2M;
- provider usa segredo somente server-side;
- operações administrativas exigem role e, para alto impacto, MFA/step-up;
- resource é sempre resolvido dentro de tenant e projeto;
- um cliente não pode consultar instância de outro cliente;
- logs mascaram telefone, token, QR e payload sensível.

Scopes recomendados:

```text
channels:read
channels:manage
whatsapp:messages:send
whatsapp:messages:read
whatsapp:media:send
whatsapp:contacts:read
whatsapp:chats:read
whatsapp:groups:read
whatsapp:groups:manage
webhooks:manage
conversations:read
conversations:write
operations:read
```

Nenhuma API key deve receber `*:manage` por padrão.

## 5. Máquina de estados Mago

### Canal

```text
provisioning -> created -> qr_pending -> connecting -> connected
connected -> syncing -> connected
connected -> disconnected -> connecting
connected -> degraded
degraded -> connected
disconnected -> logged_out
qualquer estado aberto -> failed
qualquer estado ativo -> suspended
qualquer estado final -> deleted
```

Cada transição registra:

- estado anterior;
- novo estado;
- causa segura;
- provider;
- operação relacionada;
- provider event ID;
- request ID;
- timestamp;
- ator, quando houver ação humana.

### Mensagem

```text
accepted -> queued -> sending -> provider_accepted -> sent
sent -> delivered -> read
qualquer estado não final -> failed | rejected | expired
```

O Mago não deve afirmar `delivered` apenas porque o provider aceitou a requisição. `accepted`, `sent`, `delivered` e `read` são fatos diferentes.

### Operação

```text
accepted -> running -> succeeded
accepted -> running -> failed
running -> dead_letter
accepted -> cancelled
```

Toda operação precisa de timeout. `running` indefinido é bug operacional.

## 6. Contrato de erro e diagnóstico

Todo erro público deve ter:

```json
{
  "error": {
    "code": "channel_not_connected",
    "message": "O canal precisa estar conectado antes do envio.",
    "request_id": "req_...",
    "retryable": false,
    "operation_uuid": "op_..."
  }
}
```

Catálogo inicial:

| Código | Explicação simples | Retry |
|---|---|---:|
| `invalid_api_key` | A chave não é válida | Não |
| `scope_missing` | A chave não possui essa permissão | Não |
| `tenant_access_denied` | O recurso pertence a outro ambiente | Não |
| `channel_not_connected` | O WhatsApp ainda não está conectado | Depois de conectar |
| `provider_unavailable` | O serviço externo não respondeu | Sim, com backoff |
| `provider_rejected` | O provider recusou a operação | Conforme código |
| `idempotency_conflict` | A mesma chave foi usada com outro pedido | Não |
| `quota_exceeded` | O limite do plano foi atingido | Depois do limite |
| `media_invalid` | A mídia não passou na validação | Não |
| `webhook_signature_invalid` | A assinatura não confere | Não |
| `operation_timeout` | A operação demorou demais | Consultar estado |

Uma criança entende assim: se aparece “provider indisponível”, pode tentar mais tarde; se aparece “chave inválida”, precisa corrigir a chave; se aparece “canal desconectado”, precisa reconectar o WhatsApp.

## 7. O que já existe no Mago e o que falta

| Área | Estado real | Próximo fechamento |
|---|---|---|
| Control plane | Existe | testes cross-tenant automatizados |
| API keys/scopes | Existe | rotação, expiração e exemplos |
| Lifecycle Evolution | Parcialmente pronto | E2E real com QR/pairing e timeout |
| Texto | Implementado no adapter | teste real com número opt-in |
| Mídia | Base implementada | storage assinado, MIME/size e E2E |
| Webhooks | Assinatura, retry e worker | DLQ, replay, contrato versionado |
| Inbox/conversas | Núcleo existe | assignment, regras e E2E inbound/outbound |
| Grupos/contatos/chats | Não comprovado como produto público | adapters e scopes dedicados |
| Presença/chamadas/status | Não é P0 | capability discovery e limites |
| S3/MinIO | Roadmap | storage isolado e lifecycle |
| RabbitMQ/NATS/SQS | Roadmap | abstração de transportes e operação |
| Integrações IA/CRM | Roadmap/isoladas | segredo por projeto e auditoria |
| Meta Cloud | Adapter separado | onboarding oficial e templates |
| Billing | Modelo/trial | checkout e webhook financeiro real |
| SDKs | Não estabilizados | publicar depois do contrato |

## 8. Roadmap de paridade realista

### P0 — núcleo vendável

1. Fazer o canal de laboratório chegar a `connected`.
2. Corrigir toda operação presa com timeout e reconciliação.
3. Completar texto, QR, webhook, status e retry sem duplicação.
4. Fazer backup/restore de banco e volume de sessão.
5. Documentar curl, Python e TypeScript executáveis.
6. Criar uma tela de diagnóstico que explique “o que aconteceu” e “qual é o próximo passo”.

### P1 — paridade operacional

1. Catálogo de capabilities por provider/flavor.
2. Delivery log, replay e DLQ.
3. S3/MinIO com URL assinada.
4. Contatos, chats e grupos com scopes próprios.
5. Presence com TTL e rate limit.
6. WebSocket/SSE para eventos da interface.
7. SDK TypeScript e Python.

### P2 — plataforma maior

1. RabbitMQ/NATS/SQS/Kafka conforme clientes reais.
2. Chatwoot, Typebot, Dify, N8N e IA com conectores isolados.
3. Multi-shard Evolution e limites por shard.
4. Billing recorrente e portal do cliente.
5. Status page, SLOs e suporte comercial.
6. Meta Cloud com Embedded Signup, templates e múltiplos números.

## 9. Critérios de “feito de verdade”

O recurso só pode ser marcado como pronto quando uma pessoa sem conhecimento interno consegue:

1. criar um projeto;
2. criar uma chave com a permissão mínima;
3. criar um canal;
4. entender se o canal está criado ou conectado;
5. gerar QR sem acessar banco ou container;
6. conectar um número de laboratório;
7. enviar uma mensagem com opt-in;
8. receber o status correto;
9. receber um webhook assinado;
10. repetir a requisição sem duplicar;
11. entender um erro sem olhar logs internos;
12. reconectar ou encerrar a sessão com segurança.

Se qualquer etapa exige editar banco, copiar token do container ou chamar o Manager diretamente, a experiência ainda é assistida.

## 10. Limites que devem permanecer explícitos

Evolution/WhatsApp Web não deve ser anunciado como Meta Cloud oficial. A documentação oficial da Evolution separa Baileys/WhatsApp Web da Meta Cloud e informa que cada conexão tem características próprias.[1]

Não prometer:

- aprovação de templates da Meta usando Evolution;
- WABA ou Phone Number ID quando o provider for Evolution;
- qualidade oficial ou SLA da Meta;
- imunidade a logout, bloqueio ou queda de sessão;
- suporte universal a todo recurso em todo flavor;
- entrega definitiva apenas porque houve resposta HTTP 200;
- funcionamento de recursos classificados como “homologação” sem teste.

O produto pode prometer uma camada profissional de gestão, auditoria, segurança, observabilidade e contrato. Não pode prometer que controla políticas ou disponibilidade de terceiros.

## 11. Checklist para cada nova capacidade

Antes de adicionar qualquer endpoint, responder:

- Qual provider suporta?
- É oficial Meta, compatibilidade ou ambos?
- Qual scope libera?
- É síncrono ou operação assíncrona?
- Como é a idempotência?
- Qual é o timeout?
- Qual evento confirma sucesso?
- Como o cliente consulta o estado?
- Qual é o erro retryable?
- Qual dado sensível pode aparecer?
- Existe auditoria?
- Existe teste de tenant A contra tenant B?
- Existe teste de provider indisponível?
- Existe rollback ou compensação?
- O guia de uma página explica para uma criança?

## 12. Conclusão executiva

O Mago Bot não precisa copiar a Evolution Foundation para ser melhor. Deve absorver as ideias corretas:

- catálogo amplo de capacidades;
- providers separados;
- eventos como parte central do produto;
- armazenamento de mídia profissional;
- integrações extensíveis;
- operação multi-instância;
- documentação prática.

E deve melhorar os pontos mais frágeis:

- esconder complexidade do provider sem esconder limitações;
- substituir tokens globais por identidade e scopes por projeto;
- transformar estados ambíguos em máquina de estados explicável;
- tornar retry, DLQ e replay visíveis;
- impedir cross-tenant e vazamento de segredo;
- diferenciar “aceito”, “enviado”, “entregue” e “lido”;
- dar ao operador um caminho de recuperação claro.

O marco comercial correto é **Mago Bot — Managed WhatsApp Channels**, com dois caminhos declarados: **Meta Cloud oficial** e **Evolution compatibilidade controlada**. A paridade deve ser medida por testes e contratos, não por quantidade de endpoints.

## Fontes oficiais consultadas

1. Evolution Foundation. [Evolution API — repositório e arquitetura oficial](https://github.com/evolution-foundation/evolution-api).
2. Evolution Foundation. [Create Instance](https://docs.evolutionfoundation.com.br/evolution-api/create-instance).
3. Evolution Foundation. [Recursos disponíveis](https://docs.evolutionfoundation.com.br/evolution-api/configuration/available-resources).
4. Evolution Foundation. [Webhooks e eventos](https://docs.evolutionfoundation.com.br/en/evolution-api/configuration/webhooks).
5. Evolution Foundation. [Set Presence](https://docs.evolutionfoundation.com.br/en/evolution-api/set-presence).
6. Evolution Foundation. [Variáveis de ambiente e eventos](https://docs.evolutionfoundation.com.br/evolution-api/configuration/env).
7. Evolution Foundation. [RabbitMQ e filas de eventos](https://docs.evolutionfoundation.com.br/en/evolution-api/integrations/rabbitmq).
8. Evolution Foundation. [Amazon SQS](https://docs.evolutionfoundation.com.br/en/evolution-api/integrations/sqs).
9. Evolution Foundation. [Send Media Message](https://docs.evolutionfoundation.com.br/evolution-api/send-media-message).
10. Evolution Foundation. [Site institucional](https://evolutionfoundation.com.br/).
