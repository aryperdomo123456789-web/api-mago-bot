# Auditoria de prontidão do produto API Mago Bot v1

## Veredito executivo

O diagnóstico apresentado está estrategicamente correto, mas precisa ser lido como um plano de fechamento, não como uma descrição do que já está pronto.

O Mago Bot já possui uma fundação real de control plane multi-tenant: autenticação, tenants, projetos, API keys, scopes, quotas, idempotência, operações, canais Evolution, mensagens, conversas, webhooks, uso, inbox, MFA e console operacional. Isso é substancialmente mais do que uma simples central de licenças.

Ao mesmo tempo, a produção observada em `69.197.184.45` ainda não prova um produto vendável sem assistência. O banco contém apenas 1 tenant, 1 projeto, 1 chave e 1 canal. O canal está `degraded`, o recurso provider está `provisioning`, existe uma operação `channel.create` em `running`, e foram registradas duas falhas de QR. Não há registros de mensagens outbound, webhooks de clientes, entregas de webhook, assinaturas comerciais ou entregas de e-mail.

Conclusão realista:

| Nível | Veredito |
|---|---|
| Fundação técnica | Existe e é relevante |
| MVP interno/laboratório | Sim, com correções operacionais |
| Piloto privado assistido | Possível, depois de fechar o ciclo do canal |
| SaaS público para clientes externos | Ainda não comprovado |
| API oficial Meta completa | Não; a camada Meta ainda não é produto completo |
| Produto Evolution de compatibilidade | Base existe; onboarding e prova E2E ainda faltam |

O marco correto continua sendo **API Mago Bot v1 — Managed WhatsApp Channels**, mas ele só deve ser anunciado quando um cliente externo conseguir completar o ciclo inteiro sem intervenção manual indevida.

## 1. Escopo e fonte da auditoria

Esta auditoria cruza:

- código ativo em `/opt/mago-platform/service`;
- OpenAPI exposta pelo processo em `127.0.0.1:4349`;
- containers ativos no servidor `69.197.184.45`;
- estado efetivo das tabelas PostgreSQL do control plane;
- documentação interna do produto;
- documentação oficial da Meta e da Evolution.

Data da verificação do runtime: **15/09/2026 UTC**.

A auditoria não considera uma tela, um endpoint declarado ou um container saudável como prova de capacidade comercial. Uma capacidade só é classificada como entregue quando há código, contrato, persistência, segurança e um caminho verificável de sucesso e falha.

## 2. Estado observado no servidor

### 2.1 Serviços ativos

| Serviço | Estado observado | Função |
|---|---|---|
| `mago_licensing_app` | healthy | FastAPI control plane em `127.0.0.1:4349` |
| `mago_evolution_api` | ativo | Evolution API v2.3.7 em `127.0.0.1:4348` |
| `mago_platform_db` | healthy | PostgreSQL do control plane |
| `mago_evolution_db` | healthy | PostgreSQL da Evolution |
| `mago_platform_redis` | ativo | Redis do control plane |
| `mago_evolution_redis` | ativo | Redis da Evolution |
| `mago_webhook_worker` | healthy | processamento de entregas de webhooks |
| `mago_owner_welcome_worker` | healthy | boas-vindas do owner |
| `mago_evolution_health_worker` | healthy | reconciliação/saúde de canais |

Os healthchecks mostram processos vivos e dependências básicas disponíveis. Eles não demonstram que um canal pode ser criado, conectado, usado para enviar uma mensagem e recuperar-se de uma falha.

### 2.2 Estado do banco de produção

Contagens verificadas no PostgreSQL `platform_db`:

| Entidade | Quantidade |
|---|---:|
| Tenants | 1 |
| Projetos | 1 |
| Service API keys | 1 |
| Canais Evolution | 1 |
| Integrações WhatsApp do owner | 0 |
| Entregas de boas-vindas | 0 |
| Entregas de e-mail | 0 |
| Supressões de e-mail | 0 |
| Assinaturas de webhook de clientes | 0 |
| Operações de canal | 4 |

Estado do único canal e das operações:

- canal Evolution: `degraded`;
- provider resource: `provisioning`;
- operação `channel.create`: `running`;
- operações `channel.qr`: 1 `succeeded` e 2 `failed`;
- assinatura comercial registrada: 1 `start/trialing`.

Isso significa que o ambiente está instalado, mas não está demonstrado como um ambiente de onboarding saudável.

## 3. O que o código já entrega

### 3.1 Control plane e isolamento

O sistema possui modelos e rotas para tenants, memberships, projetos e recursos de provider. A API resolve o tenant a partir da sessão ou da API key e verifica o vínculo do projeto antes de executar operações.

Há suporte a:

- sessão server-side;
- cookies `HttpOnly`, `Secure`, `SameSite` e prefixo `__Host-`;
- API keys armazenadas por hash;
- exibição do token somente na criação;
- scopes;
- RBAC de tenant;
- MFA de plataforma;
- auditoria;
- revogação de chave;
- quotas por plano;
- rate limit distribuído;
- validação de endpoint webhook contra SSRF.

Essa é uma boa fundação de segurança. Ainda precisa de testes de autorização cross-tenant e de uma política formal de rotação, expiração e MFA obrigatório para operações de alto impacto.

### 3.2 Projetos, chaves e API pública

Existem rotas para criar/listar projetos, emitir/listar/revogar chaves e consultar scopes. A chave criada é limitada ao projeto e deve conter `whatsapp:messages:send` para envio.

O envio público de mensagem exige:

- API key válida;
- scope de envio;
- projeto ativo e pertencente ao tenant da chave;
- `X-Idempotency-Key` com tamanho mínimo;
- quota por minuto e por dia;
- exatamente um provider resource ativo, salvo seleção explícita;
- canal Evolution conectado quando o provider é Evolution;
- circuito de provider disponível;
- operação persistida para acompanhamento.

O desenho de idempotência é adequado: a mesma chave com o mesmo payload deve ser replay, enquanto a mesma chave com payload diferente deve produzir conflito.

O que ainda precisa ser provado em E2E é a concorrência: duas requisições simultâneas com a mesma chave, timeout depois do envio provider e retry do cliente sem duplicar mensagem.

### 3.3 Canais Evolution

O código já possui:

- criação de canal vinculado a `organization_id` e `project_id`;
- `channel_uuid` público;
- nome interno da instância escondido do contrato recomendado;
- provider flavor `evolution_api` ou `evolution_go`;
- criação de instância na Evolution;
- token e segredo de webhook cifrados;
- QR Code;
- status;
- conexão;
- reconexão;
- desconexão;
- exclusão;
- telefone e JID persistidos;
- eventos de instância;
- webhook assinado por segredo do endpoint;
- eventos normalizados para mensagens, status e conexão.

Isso confirma que a direção `project_uuid -> channel_uuid -> provider -> instance` já está representada. O nome interno da Evolution não precisa ser exposto ao cliente.

Lacunas observadas:

- o canal real em produção não convergiu para `connected`;
- a operação de criação ficou `running`;
- o recurso provider ficou `provisioning`;
- falta uma reconciliação comprovada entre operação, banco, provider e painel;
- falta teste de restore do volume de sessões;
- falta comprovar envio e recebimento com um cliente externo;
- falta definir limite, expiração e reemissão de QR no contrato público;
- falta diferenciar claramente falha de API, sessão deslogada, QR expirado e WhatsApp bloqueado.

### 3.4 Mensagens

O adapter Evolution suporta texto e mídia com validação de URL HTTPS, bloqueio de hosts privados, limite de tamanho e persistência do provider message ID.

O código também contém circuit breaker, rate limit, quota, operação assíncrona e estado de mensagem. Isso é uma base correta.

O produto ainda precisa fechar:

- contrato público documentado para cada tipo de mensagem;
- limites explícitos de tamanho por mídia;
- estados provider normalizados;
- reconciliação por `MESSAGES_UPDATE`/`SEND_MESSAGE_UPDATE`;
- comportamento quando a API aceita a operação, mas o cliente perde a resposta;
- política de mensagens duplicadas e replay;
- teste real de texto, imagem, documento e erro provider.

### 3.5 Webhooks de clientes

Há configuração, rotação e desativação de webhooks de projeto. O sistema gera entregas, aplica assinatura HMAC, mantém tentativas e usa worker separado. O endpoint de entrada Evolution também aplica idempotência e valida o canal.

A Evolution documenta eventos como `QRCODE_UPDATED`, `CONNECTION_UPDATE`, `MESSAGES_UPSERT`, `MESSAGES_UPDATE` e `SEND_MESSAGE`; o sistema já está alinhado com esse tipo de ciclo de evento.[1]

A Meta documenta webhooks para mensagens recebidas, status de mensagens e mudanças operacionais da conta. O endpoint deve ser HTTPS, validar assinatura e responder rapidamente; a Meta pode reenviar eventos e payloads podem chegar a 3 MB.[2]

O código já tem endpoint Meta com challenge e `X-Hub-Signature-256`, mas isso não equivale a um onboarding Meta completo. Ainda faltam validação de templates, configuração assistida, associação segura de múltiplos números e teste E2E com payloads reais.

### 3.6 Conversas e inbox

O Conversation Core possui customer profiles, identities, conversations, events, status e inbox queues. Há rotas de listar, criar, atribuir, reivindicar, anotar, reabrir, resolver, liberar e adiar conversas.

Isso é um bom núcleo de CRM/inbox, mas não deve ser confundido com o produto mínimo de API. Para a primeira venda, a prioridade é canal, mensagem, evento, operação e webhook. Inbox avançado pode ser uma vantagem, não um bloqueador do primeiro piloto, desde que não seja prometido como omnichannel completo.

### 3.7 E-mail

Existe uma fundação de e-mail transacional: identidades de remetente, deliveries, supressões, eventos de provider, integração Resend e rotas operacionais. Há também um `email_worker.py` implementado.

Contudo, o Compose de produção observado não inicia esse worker. Não há evidência de uma fila de e-mail funcionando em produção, domínios verificados, caixas de entrada, aliases ou serviço de mail hospedado.

Portanto, o produto de e-mail não deve ser anunciado como pronto. Ele é uma fundação transacional separada do produto WhatsApp.

### 3.8 Trial, planos e billing

Há catálogo de planos, trial, ativação, conta de cliente, assinatura no banco, limites e uso. Isso permite uma experiência de demonstração e controle de quota.

Não foi encontrada evidência, nas rotas expostas e no runtime auditado, de um fluxo de billing comercial completo com:

- checkout real;
- customer e subscription no provedor de pagamentos;
- webhook assinado do provedor;
- falha de cobrança;
- renovação;
- cancelamento;
- suspensão automática de acesso;
- portal do cliente;
- reconciliação financeira.

Logo, “billing mínimo” é uma etapa futura, não uma capacidade já entregue.

## 4. Verificação do posicionamento proposto

### 4.1 O que está correto

O posicionamento de “infraestrutura unificada para conectar canais WhatsApp, gerenciar sessões, enviar mensagens e receber eventos por API” é tecnicamente coerente com a fundação atual.

O cliente inicial sugerido também é correto: software house, agência, integrador ou SaaS que prefere consumir uma camada pronta a construir QR, reconexão, webhooks, idempotência, filas e auditoria.

Também está correta a decisão de não vender a Evolution como “API oficial equivalente à Meta”. A Evolution é uma camada de compatibilidade baseada em sessão WhatsApp Web; sua experiência pode ser profissional, mas seu comportamento operacional e seu risco não são iguais aos da WhatsApp Business Platform Cloud API.

### 4.2 O que precisa ser corrigido

O texto apresentado chama o produto de API pública como se o ciclo estivesse comprovado. Hoje isso é prematuro.

Também é necessário separar três produtos:

1. **API Mago Bot**: control plane, API keys, projetos, canais, operações, webhooks e quotas.
2. **Provider Evolution**: conexão por QR, sessão, envio e eventos de compatibilidade.
3. **Provider Meta Cloud**: canal oficial, tokens, WABA, Phone Number ID, templates e regras Meta.

O cliente deve conhecer apenas `project_uuid`, `channel_uuid`, operação e evento. O provider é um detalhe de implementação, mas suas capabilities, custos, limites e risco precisam aparecer no estado do canal.

Não se deve normalizar diferenças importantes como se fossem iguais:

| Tema | Meta Cloud | Evolution |
|---|---|---|
| Onboarding | credenciais/Business Platform | QR ou pairing |
| Sessão | gerenciada pela Meta | depende de sessão WhatsApp Web |
| Primeira mensagem | templates/políticas Meta | texto/mídia conforme provider |
| Status | webhooks oficiais | eventos Evolution |
| Risco de desconexão | operacional/API | sessão pode cair e exigir pareamento |
| Compliance | canal oficial | compatibilidade, sem chamar de oficial |
| SLA | contrato/provider Meta | depende da operação Mago + Evolution + WhatsApp |

## 5. Contrato de produto v1

### 5.1 Entidades públicas

O contrato externo recomendado é:

```text
organization_uuid
project_uuid
channel_uuid
operation_uuid
message_uuid
webhook_subscription_uuid
```

Nunca expor como dependência pública:

- nome interno da instância Evolution;
- token da instância;
- token Meta;
- nome de container;
- host interno;
- ID de banco;
- segredo do webhook.

### 5.2 Fluxo mínimo vendável

O fluxo mínimo é:

```text
signup
  -> email verification
  -> login
  -> create project
  -> create API key
  -> create channel
  -> connect
  -> obtain QR
  -> scan QR
  -> provider connected
  -> register signed webhook
  -> send opt-in text with idempotency key
  -> receive normalized status/event
  -> query operation/message
  -> retry same request without duplicate
```

Esse fluxo precisa funcionar em ambiente limpo, com um usuário que não conhece o banco nem a Evolution. Se o operador precisar corrigir manualmente banco, container ou token, o fluxo ainda não é self-service.

### 5.3 Estados mínimos

Canal:

```text
provisioning
created
qr_pending
pairing_pending
connecting
connected
syncing
disconnected
degraded
logged_out
suspended
failed
deleted
```

Operação:

```text
accepted
running
succeeded
failed
cancelled
dead_letter
```

Mensagem:

```text
accepted
queued
sending
provider_accepted
sent
delivered
read
failed
rejected
expired
```

Os estados devem ter transições permitidas e motivo persistido. O painel não deve mostrar apenas `degraded`; deve mostrar a última causa conhecida, horário, provider, operação relacionada e ação de recuperação.

## 6. Critérios de pronto por bloco

| Bloco | Já existe | Falta para declarar pronto |
|---|---|---|
| Projeto | signup, tenant, projeto, sessão | teste limpo de isolamento e UX completa |
| API key | hash, scopes, revogação | rotação, expiração visível, exemplos e teste concorrente |
| Canal | Evolution create/connect/QR/status | convergência de estado e ciclo E2E comprovado |
| Mensagem | texto/mídia, quota, idempotência | reconciliação de status e matriz de erros |
| Webhook | assinatura, retry, worker | contrato versionado, replay, DLQ operável e teste externo |
| Operação | tabela e rotas | operação não pode ficar `running` indefinidamente |
| Segurança | RBAC, MFA, cifragem, SSRF | threat model, rotação, auditoria completa e testes cross-tenant |
| Observabilidade | health, metrics, workers | alertas, SLO, dashboards e correlação ponta a ponta |
| Backup | volumes e bancos existem | backup automático, restore isolado e teste periódico |
| Trial | catálogo, criação, ativação | expiração automática, suspensão e upgrade real |
| Billing | modelo de assinatura e planos | checkout, provider webhook e reconciliação |
| DX | OpenAPI e rotas | guia 5 minutos, exemplos curl/Node/Python, SDK e erros |
| Escala | provider flavor e limites | shards, isolamento de volumes e carga medida |

## 7. Plano de implementação realista

### Fase 0 — Reproduzir o incidente atual

Antes de novas features, explicar o estado `degraded/provisioning/running` do canal atual.

Entregas:

- correlacionar `platform_operations`, `evolution_instances`, `provider_resources` e `evolution_instance_events`;
- corrigir operações presas com timeout e finalização idempotente;
- registrar código e mensagem de falha sem segredo;
- validar comunicação interna do control plane com a Evolution;
- confirmar se a instância interna existe e qual é seu estado;
- testar criação/QR em um canal descartável, sem tocar no canal de produção;
- documentar a causa antes de mudar o provider.

Critério: criação e QR passam em ambiente limpo, ou o erro é reproduzível e explicado.

### Fase 1 — Suíte E2E de segurança e ciclo de canal

Criar ambiente de teste separado com banco, Redis e Evolution descartável. Testar:

- signup e verificação;
- login/logout e MFA;
- tenant A não lê projeto de tenant B;
- chave revogada não envia;
- escopo ausente retorna erro correto;
- criação de projeto;
- criação de canal;
- QR e expiração;
- conexão;
- webhook assinado;
- envio opt-in;
- status da mensagem;
- replay de idempotência;
- payload divergente na mesma idempotency key;
- provider indisponível;
- retry e dead letter;
- rotação/desativação do webhook.

Critério: pipeline automatizado verde, com banco limpo e evidência de payloads.

### Fase 2 — Estado confiável e reconciliação

Implementar:

- máquina de estados explícita;
- `operation_timeout_at`;
- worker de reconciliação de operações;
- heartbeat da instância provider;
- sincronização periódica do status Evolution;
- correlação por request ID, operation ID e provider event ID;
- alerta para `running` antigo, `provisioning` antigo e `degraded` sem causa;
- botão de replay de evento apenas com auditoria e permissão.

Critério: nenhum estado aberto indefinidamente; painel e provider convergem após falha e recuperação.

### Fase 3 — Backup e restore

Separar e testar:

- PostgreSQL do control plane;
- PostgreSQL da Evolution;
- Redis necessário à durabilidade, se aplicável;
- volumes de sessão Evolution;
- arquivos de configuração sem segredos em texto;
- chaves de criptografia guardadas fora do backup público.

O restore deve ser feito em ambiente isolado, com DNS de teste e sem disparar webhooks para clientes reais.

Critério: restaurar um canal e recuperar histórico/configuração sem duplicar mensagens ou expor segredos.

### Fase 4 — Piloto privado

Começar com poucos integradores e suporte assistido. O piloto deve possuir:

- limites baixos;
- sandbox ou números de teste;
- termos claros sobre Evolution;
- logs e suporte com request ID;
- procedimento de reconexão;
- proibição de spam e disparos sem consentimento;
- relatório semanal de falhas.

Não prometer SLA, volume ou permanência de sessão antes de medir.

### Fase 5 — Billing e trial comercial

Adicionar provider de pagamentos somente depois que o uso for medido. O mínimo comercial inclui:

- checkout;
- subscription ID externo;
- webhook assinado;
- idempotência de eventos de cobrança;
- estados `trialing`, `active`, `past_due`, `canceled`, `suspended`;
- suspensão de envio quando o plano expira;
- reativação após pagamento;
- página de uso e limite.

Webhooks de billing devem ser tratados como eventos assíncronos e idempotentes, seguindo o mesmo padrão de verificação, retry e reconciliação usado para mensagens.[3]

### Fase 6 — Developer experience

Publicar:

- OpenAPI revisada;
- guia “primeiro canal em 5 minutos”;
- curl completo;
- Node.js;
- Python;
- exemplos de webhook assinado;
- catálogo de erros;
- exemplos de idempotência;
- changelog e versionamento;
- SDK somente depois de estabilizar o contrato.

### Fase 7 — Escala Evolution

Quando houver clientes pagantes:

- introduzir shards;
- registrar `channel -> provider -> instance -> shard`;
- volume persistente próprio por sessão;
- quotas por shard;
- limites de CPU, memória, PIDs e conexões;
- healthcheck real;
- backup por shard;
- distribuição de novas instâncias;
- hosts separados para reduzir blast radius.

Várias instâncias no mesmo host não são alta disponibilidade. É apenas isolamento lógico.

## 8. Segurança e operação obrigatórias

### Segredos

- nunca devolver token em GET;
- cifrar tokens e segredos em repouso;
- separar chave de criptografia do banco;
- permitir rotação sem downtime;
- auditar quem criou, substituiu ou removeu segredo;
- nunca gravar Authorization, API key, QR bruto ou payload sensível no log;
- mascarar telefone e dados pessoais onde não forem necessários.

### Webhooks

- HTTPS obrigatório;
- HMAC por assinatura;
- timestamp/nonce contra replay quando o contrato permitir;
- limite de tamanho;
- deduplicação por provider event ID;
- resposta rápida e processamento assíncrono;
- retry com backoff;
- dead letter com replay controlado;
- isolamento por tenant/projeto;
- validação de eventos não mapeados.

### Mensageria

- exigir opt-in quando a mensagem for iniciada pelo negócio;
- limitar envio por tenant, projeto, chave e destino;
- bloquear spam e loops de webhook;
- não enviar senha ou segredo por WhatsApp/e-mail;
- declarar claramente que Evolution não é Meta Cloud API;
- registrar consentimento e origem quando o produto oferecer automações.

## 9. Métricas e SLOs para o piloto

Medir antes de prometer:

- taxa de criação de canal bem-sucedida;
- tempo de QR até conexão;
- tempo em `provisioning`;
- tempo em `degraded`;
- taxa de envio aceito pelo provider;
- taxa de falha por código;
- latência p50/p95 de envio;
- tempo de entrega de webhook;
- quantidade de duplicatas evitadas;
- tamanho da fila;
- idade máxima da fila;
- dead letters;
- reconnects por canal/dia;
- incidentes de sessão perdida;
- consumo por tenant e shard.

SLO só deve ser publicado depois de uma série de dados suficiente. “Container healthy” não é SLO.

## 10. Go/no-go para declarar API Mago Bot v1

### Go para piloto privado

- canal Evolution conectado em ambiente limpo;
- cliente externo completa onboarding com instrução pública;
- envio de texto opt-in funciona;
- webhook assinado chega ao endpoint externo;
- status de mensagem é consultável;
- retry não duplica;
- canal desconecta e reconecta;
- logs permitem diagnosticar uma operação por ID;
- backup e restore foram executados;
- termos e limites da Evolution estão explícitos.

### No-go para venda pública

Qualquer item abaixo impede declarar produto pronto:

- operação fica `running` sem timeout;
- recurso fica `provisioning` sem reconciliar;
- cliente precisa editar banco ou container;
- chave de tenant acessa outro tenant;
- webhook aceita payload sem assinatura;
- retry duplica mensagens;
- não há backup testado;
- billing suspende ou libera acesso manualmente;
- produto anuncia Evolution como API oficial;
- não há caminho de suporte para sessão desconectada.

## 11. Decisão final

O texto de posicionamento está certo na direção e errado apenas se for usado como prova de prontidão atual. O Mago Bot não precisa inventar dezenas de módulos agora. Precisa provar o núcleo que já começou a construir.

A ordem correta é:

1. resolver o canal real `degraded/provisioning`;
2. automatizar o ciclo E2E em ambiente isolado;
3. fechar reconciliação de estados;
4. testar backup/restore;
5. executar piloto privado;
6. adicionar billing e documentação de desenvolvedor;
7. escalar Evolution com shards somente depois de medir.

O produto que pode ser vendido primeiro é **uma camada profissional de integração WhatsApp com adapters Meta e Evolution**, não “uma API oficial equivalente à Meta”. A camada oficial e a camada Evolution podem compartilhar contrato, operação, auditoria e experiência; não devem esconder as diferenças de compliance, sessão, limites e risco.

## Fontes e referências

1. Evolution Foundation, “Webhooks”, eventos, configuração por instância, QR, conexão e mensagens: [documentação oficial](https://github.com/evolution-foundation/evolution-docs/blob/main/docs/02-Configuration/Webhooks.md).
2. Meta / WhatsApp Business Platform, webhooks, permissões, payloads, retries e assinatura: [coleção oficial de Webhooks](https://www.postman.com/meta/whatsapp-business-platform/folder/lboq68h/webhooks) e [documentação de referência](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/).
3. Stripe, webhooks de assinaturas, eventos assíncronos, falhas de cobrança e mudança de status: [Subscription webhooks](https://docs.stripe.com/billing/subscriptions/webhooks).
4. Meta / WhatsApp Business Platform, categorias e cobrança por mensagens entregues: [pricing oficial](https://whatsappbusiness.com/products/platform-pricing/).
5. Evolution Foundation, criação de instância, QR e webhook na criação: [Create Instance](https://github.com/evolution-foundation/evolution-docs/blob/main/docs/03-Instance%20contoller/00-create-instance.md).

