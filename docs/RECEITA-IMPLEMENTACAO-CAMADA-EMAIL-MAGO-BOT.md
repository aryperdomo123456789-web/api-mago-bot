# Receita de implementação da camada de e-mail do Mago Bot

## Objetivo

Este documento define como transformar a plataforma atual do Mago Bot em uma camada de e-mail multi-tenant, com:

- envio transacional por API;
- recebimento por webhook e/ou caixa IMAP/JMAP;
- domínios personalizados;
- caixas profissionais, aliases e quotas;
- SPF, DKIM, DMARC e verificação automática;
- painel operacional para o owner;
- API para clientes criarem e enviarem e-mails;
- isolamento entre CRM, Evolution API e infraestrutura de e-mail.

O objetivo é encaixar a capacidade de e-mail no sistema existente, preservando o CRM e a Evolution API.

## 1. Diagnóstico do sistema atual

### 1.1 Serviços em produção

No servidor `69.197.184.45`, o estado observado é:

| Superfície | Função | Estado |
|---|---|---|
| `mago-bot.com` | CRM e login do dono | ativo via PM2 |
| `app.mago-bot.com` | portal/control-plane | ativo no container de licenciamento |
| `evo-api.mago-bot.com` | Evolution e console operacional | ativo; proxy especial já configurado |
| `mago_licensing_app` | API/control-plane em `127.0.0.1:4349` | saudável |
| `mago_evolution_api` | Evolution em `127.0.0.1:4348` | ativo |
| PostgreSQL/Redis | dados do control-plane e Evolution | saudáveis |

As portas SMTP/IMAP usuais não estão ocupadas neste momento. Isso permite instalar uma camada de e-mail sem competir com os processos atuais, mas não justifica misturar o armazenamento de mensagens diretamente ao banco do CRM.

### 1.2 O que já existe no código da plataforma

O backend em `/opt/mago-platform/service` já contém uma base transacional:

- `EmailSenderIdentity`: remetente permitido por tenant;
- `EmailDelivery`: fila, tentativas, status, provider ID e erros;
- `EmailSuppression`: bloqueio de destinatários após bounce/complaint;
- `EmailProviderEvent`: eventos idempotentes do provider;
- `email_service.py`: renderização de mensagens de boas-vindas, verificação e reset;
- `email_worker.py`: tentativa de envio com retry e limite diário;
- `providers/resend_email.py`: adaptador Resend;
- `routes/email_webhooks.py`: validação de assinatura Svix/Resend;
- `routes/email_ops.py`: remetentes, entregas, eventos e supressões;
- seção “E-mail transacional” no Operations Console.

O esquema `0007_email_transacional.sql` confirma que essa parte foi planejada como envio transacional, não como serviço completo de caixas de e-mail.

### 1.3 Lacunas reais encontradas

O runtime atual tem as tabelas de e-mail, mas sem registros. A API expõe apenas:

```text
/v1/ops/email/senders
/v1/ops/email/deliveries
/v1/ops/email/events
/v1/ops/email/suppressions
/v1/webhooks/email/resend
```

Não há ainda:

- worker de e-mail listado no `docker-compose.production.yml`;
- domínio de envio com estado de verificação;
- publicação/checagem de SPF, DKIM, DMARC e MX;
- caixas de entrada, aliases, encaminhamentos ou quotas;
- mensagens recebidas persistidas;
- anexos e armazenamento de objetos;
- templates editáveis no painel;
- API pública de envio para tenants;
- API de criação de API keys de e-mail com escopos próprios;
- rate limit e orçamento por domínio/tenant para e-mail;
- integração Cloudflare para DNS;
- rotação de provider;
- painel de saúde de entrega por domínio/provider.

Há também duas decisões importantes no código atual:

1. `RESEND_DRY_RUN` fecha o envio real por padrão; isso é seguro, mas impede produção até haver uma decisão explícita.
2. `EMAIL_ALLOWED_SENDER_DOMAINS` usa `app.mago-bot.com` como padrão; para o produto pretendido, o domínio permitido precisa passar a ser uma entidade verificada no banco, não uma variável global.

## 2. Referências de produto e o que copiar

### Resend

O Resend trabalha com domínios verificados, SPF, DKIM, retorno personalizado, estados de verificação e eventos como sent, delivered, bounced, complained, failed e received. Também oferece recebimento por webhook e recuperação do conteúdo completo da mensagem. [Resend — domínios](https://resend.com/docs/dashboard/domains/introduction) [Resend — eventos](https://resend.com/docs/webhooks/event-types) [Resend — receiving](https://resend.com/docs/knowledge-base/how-can-i-receive-emails-with-resend)

O padrão a copiar é: domínio → DNS → verificação → remetente autorizado → envio → evento → supressão.

### Mailgun

O Mailgun separa a API por domínio, suporta envio REST/SMTP, variáveis de mensagem, envio em lote, consulta de eventos e rotas de recebimento. [Mailgun — envio](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/messages) [Mailgun — domínios](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/domains) [Mailgun — eventos](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/events/get-v3-domain_name-events)

O padrão a copiar é: cada domínio possui identidade, credenciais/escopos, eventos, fila e regras de inbound.

### Postmark

O Postmark organiza a operação por servidores/streams, separando ambientes e tipos de tráfego. A API oferece inbound webhook, delivery, bounce, click, open, suppressions, templates e estatísticas. Seus webhooks são verificados e podem ser pausados quando falham repetidamente. [Postmark — servidores](https://postmarkapp.com/developer/api/servers-api) [Postmark — webhooks](https://postmarkapp.com/developer/webhooks/webhooks-overview)

O padrão a copiar é: separar transacional de broadcast, ter endpoint testável, estado de verificação e pausa segura em caso de falhas.

### Amazon SES

O SES usa identities verificadas e configuration sets. Um configuration set associa eventos de envio, entrega, bounce, complaint, delay e engajamento a destinos de observabilidade. [AWS SES — configuration sets](https://docs.aws.amazon.com/ses/latest/dg/using-configuration-sets.html) [AWS SES — event destinations](https://docs.aws.amazon.com/ses/latest/dg/event-destinations-manage.html)

O padrão a copiar é: cada envio recebe tags de tenant, projeto, campanha e mensagem; os eventos retornam para uma fila/endpoint idempotente.

### Mailcow e Stalwart

Para caixas profissionais, o Mailcow oferece UI para domínios, caixas, aliases, DKIM, TLS, quotas, antispam, antivírus e webmail. [Mailcow — recursos](https://mailcow.github.io/mailcow-docs/)

O Stalwart oferece SMTP, IMAP, POP3, JMAP, WebUI, gerenciamento de contas/domínios, quotas, Sieve, API administrativa e métricas. [Stalwart — visão geral](https://www.stalwart.email/mail-server/) [Stalwart — API](https://stalw.art/docs/development/api/)

Recomendação: usar Resend/SES/Mailgun/Postmark para o primeiro núcleo de entrega transacional e Stalwart ou Mailcow para caixas profissionais. Uma caixa de e-mail não deve ser simulada apenas com uma tabela de eventos do provider.

## 3. Arquitetura recomendada

```text
                         ┌──────────────────────────────┐
                         │ app.mago-bot.com              │
                         │ painel customer/admin        │
                         └──────────────┬───────────────┘
                                        │ HTTPS
                         ┌──────────────▼───────────────┐
                         │ api.mago-bot.com               │
                         │ Email Control Plane            │
                         │ auth, tenants, quotas, audit  │
                         └───────┬──────────┬────────────┘
                                 │          │
                    ┌────────────▼───┐  ┌───▼────────────────┐
                    │ Delivery layer │  │ Mailbox layer      │
                    │ Resend/SES/etc │  │ Stalwart/Mailcow   │
                    └───────┬────────┘  └───┬────────────────┘
                            │               │
                    outbound events   JMAP/IMAP/SMTP/inbound
                            │               │
                         ┌──▼───────────────▼──┐
                         │ webhook/queue/events │
                         │ PostgreSQL + Redis    │
                         └──────────────────────┘
```

`evo-api.mago-bot.com` deve continuar reservado para Evolution/compatibilidade. O e-mail deve ser adicionado ao control-plane em `4349`, com rotas `/v1/mail/*`; não deve ser acoplado às rotas da Evolution em `4348`.

### Separação de tráfego

- transacional: reset, verificação, onboarding e notificações;
- produto/API: e-mails enviados por API por tenant;
- inbound: mensagens recebidas, replies e webhooks;
- mailbox: acesso humano por webmail, IMAP ou JMAP;
- broadcast: fase posterior, com regras de consentimento e descadastro próprias.

Não misturar os quatro fluxos em uma única fila sem `message_class`, `tenant_id`, `project_id`, `provider`, `idempotency_key` e `suppression_policy`.

## 4. Modelo de dados proposto

Manter as tabelas atuais e adicionar:

```text
email_domains
  id, tenant_id, domain, status, provider, verification_state,
  dkim_selector, return_path, inbound_mode, cloudflare_zone_id,
  created_at, verified_at, last_checked_at

email_dns_records
  id, domain_id, type, name, value, purpose, status,
  provider_record_id, observed_value, last_checked_at

email_mailboxes
  id, domain_id, local_part, address, status, quota_bytes,
  provider_account_id, encrypted_secret_ref, created_at

email_aliases
  id, domain_id, source_address, destination_address, status

email_inbound_messages
  id, tenant_id, domain_id, mailbox_id, provider_message_id,
  message_id, from_email, to_email, subject, text_body_ref,
  html_body_ref, headers_ref, received_at, status

email_attachments
  id, inbound_message_id, object_key, filename, content_type,
  size_bytes, sha256, malware_status

email_api_keys
  id, tenant_id, project_id, prefix, token_hash, scopes,
  rate_limit, daily_limit, expires_at, revoked_at

email_templates
  id, tenant_id, project_id, slug, version, subject_template,
  html_template, text_template, status

email_message_attempts
  id, delivery_id, provider, attempt_no, status, response_code,
  provider_message_id, error_code, latency_ms, created_at

email_webhook_deliveries
  id, provider, event_id, event_type, payload_ref, status,
  attempt_count, next_attempt_at, processed_at
```

O corpo completo de mensagens e anexos deve ir para armazenamento de objetos com criptografia, não para colunas abertas do PostgreSQL. O banco deve manter metadados, índices, estado, referências e auditoria.

## 5. API pública proposta

### Domínios

```text
POST   /v1/mail/domains
GET    /v1/mail/domains
GET    /v1/mail/domains/{domain_id}
POST   /v1/mail/domains/{domain_id}/verify
GET    /v1/mail/domains/{domain_id}/dns-records
DELETE /v1/mail/domains/{domain_id}
```

O cadastro deve retornar os registros DNS exigidos e nunca considerar o domínio pronto antes de SPF/DKIM e as validações obrigatórias estarem confirmadas.

### Caixas e aliases

```text
POST   /v1/mail/domains/{domain_id}/mailboxes
GET    /v1/mail/domains/{domain_id}/mailboxes
PATCH  /v1/mail/mailboxes/{mailbox_id}
DELETE /v1/mail/mailboxes/{mailbox_id}
POST   /v1/mail/domains/{domain_id}/aliases
DELETE /v1/mail/aliases/{alias_id}
```

Senhas de caixas nunca retornam pela API depois da criação. Para integração, usar senha de aplicativo ou OAuth/JMAP conforme o servidor escolhido.

### Envio

```text
POST /v1/mail/send
Authorization: Bearer mb_live_...
Idempotency-Key: tenant-project-message-unique-key
```

Payload mínimo:

```json
{
  "from": "notificacoes@cliente.com",
  "to": ["destinatario@example.com"],
  "reply_to": "suporte@cliente.com",
  "subject": "Pedido recebido",
  "html": "<p>...</p>",
  "text": "Pedido recebido",
  "template": "pedido_recebido",
  "variables": {"order_id": "123"},
  "tags": {"kind": "transactional", "order": "123"}
}
```

Resposta inicial: `202 Accepted`, `message_id`, `status=queued`. O cliente não deve ficar esperando o provider entregar a mensagem.

### Eventos e recebimento

```text
POST /v1/webhooks/email/{provider}
POST /v1/mail/inbound/{provider}
GET  /v1/mail/messages
GET  /v1/mail/messages/{message_id}
POST /v1/mail/messages/{message_id}/attachments/{attachment_id}/download
```

Todo webhook precisa de assinatura, timestamp, replay protection, idempotência por provider/event ID e resposta rápida `2xx`. O processamento pesado deve ir para Redis/BullMQ ou worker dedicado.

## 6. Painel do owner

O Operations Console existente já possui a entrada “E-mail transacional”. Ela deve evoluir para cinco áreas:

### Visão geral

- estado dos providers;
- fila pendente, sending, failed e dead-letter;
- entregabilidade por domínio;
- bounces, complaints e suppressions;
- uso diário/mensal por tenant;
- saúde dos webhooks;
- worker/queue heartbeat.

### Domínios e DNS

- cadastrar domínio;
- escolher provider;
- mostrar SPF/DKIM/DMARC/MX;
- copiar registros;
- verificar agora;
- mostrar divergência entre esperado e observado;
- provisionar DNS via Cloudflare apenas com autorização limitada;
- bloquear ativação se a autenticação estiver incompleta.

### Caixas profissionais

- criar caixa;
- alterar quota;
- resetar senha;
- criar alias;
- encaminhar mensagens;
- suspender/reativar;
- mostrar acesso webmail/IMAP/JMAP;
- mostrar consumo de armazenamento.

### API e envio

- criar projeto de e-mail;
- emitir/revogar API keys;
- escopos `mail.send`, `mail.domains.read`, `mail.messages.read`, `mail.webhooks.write`;
- limitar por minuto/dia;
- escolher remetente;
- testar envio;
- consultar logs sem expor corpos ou segredos.

### Templates e eventos

- rascunho/publicado/arquivado;
- versões imutáveis;
- preview HTML/texto;
- variáveis declaradas;
- eventos sent/delivered/delayed/bounced/complained/failed/received;
- reprocessamento seguro de webhook;
- exportação auditada.

## 7. Cloudflare e DNS

Para a zona `mago-bot.com`, usar um Account API Token ou User API Token limitado à zona e ao DNS. A Cloudflare recomenda tokens em vez de Global API Keys e permite restringir o token por zona, IP e duração. [Cloudflare — criação de API Token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)

Permissões iniciais:

```text
Zone Read
DNS Read
DNS Write
Cache Purge — somente se realmente necessário
```

O token fica somente no backend, cifrado e fora do frontend, logs e banco em texto aberto. Toda mutação deve gerar `AuditEvent` com actor, tenant, zone, record, before/after, request ID e resultado.

Para domínios de clientes:

- não pedir Global API Key;
- preferir token limitado à zona do cliente;
- ou usar OAuth/Cloudflare for SaaS para hostnames HTTP;
- para e-mail, entregar os registros MX/SPF/DKIM/DMARC e aguardar a validação do DNS do cliente.

Cloudflare for SaaS é apropriado para custom hostnames e SSL HTTP, não substitui a configuração de MX de uma caixa de e-mail. [Cloudflare for SaaS](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/)

Regra essencial: registros de e-mail não devem ficar proxied. `mail`, MX, SPF, DKIM e DMARC devem ser DNS-only conforme o provider exigir.

## 8. Segurança e entregabilidade

### Segurança da aplicação

- owner MFA obrigatório;
- RBAC separado para `platform_superadmin`, `platform_operator`, `platform_support` e tenant;
- API keys armazenadas somente por hash;
- segredos de provider cifrados com chave fora do banco;
- logs sem tokens, corpos, senhas ou anexos;
- rate limit por tenant, projeto, IP e remetente;
- `Idempotency-Key` obrigatório para envio;
- limite de tamanho para HTML, texto e anexos;
- sanitização de HTML e antivírus para inbound;
- retenção configurável e exclusão por tenant;
- trilha de auditoria para todas as mutações.

### Entregabilidade

- separar domínio operacional do domínio transacional, por exemplo `send.mago-bot.com`;
- SPF único por domínio, sem criar registros conflitantes;
- DKIM rotacionável por selector;
- DMARC começando em `p=none`, depois `quarantine`, e finalmente `reject` quando os relatórios estiverem corretos;
- Return-Path/bounce domain separado;
- supressão global para hard bounce e complaint;
- opt-out por tenant/campanha;
- não misturar marketing e mensagens transacionais no mesmo stream;
- warm-up de domínio/IP;
- monitorar blocklists e taxas de bounce/complaint.

## 9. Plano de implementação seguro

### Fase 0 — congelamento e observabilidade

1. Backup PostgreSQL, Redis e volumes.
2. Criar um `mail-production-readiness` checklist.
3. Adicionar métricas para o worker atual.
4. Não ativar envio real ainda.

### Fase 1 — corrigir o núcleo atual

1. Adicionar o serviço `email-worker` ao Compose, usando `python3 -m app.email_worker`.
2. Adicionar healthcheck de heartbeat.
3. Corrigir o default de domínio para configuração por banco.
4. Adicionar provider adapter interface: `send`, `get_domain`, `verify_domain`, `create_webhook`.
5. Manter Resend como primeiro adapter.
6. Adicionar testes unitários para retry, suppressions, assinatura e idempotência.
7. Criar endpoint de teste que só funciona para owner/operator.

### Fase 2 — domínios e DNS

1. Criar `email_domains` e `email_dns_records`.
2. Integrar Resend/SES/Mailgun para retornar os registros exigidos.
3. Criar Cloudflare DNS adapter com dry-run.
4. Adicionar aprovação explícita antes de criar/deletar registros.
5. Verificar DNS por polling com backoff.
6. Somente marcar `verified` quando todas as condições necessárias passarem.

### Fase 3 — API transacional

1. Criar `/v1/mail/send`.
2. Reusar `EmailDelivery`, mas adicionar `project_id`, provider, tags e attempts.
3. Adicionar templates versionados.
4. Adicionar API keys com scopes e quotas.
5. Adicionar envio em lote com limite e idempotência por item.
6. Implementar webhooks assinados e reprocessamento.

### Fase 4 — recebimento

1. Começar com inbound webhook do provider.
2. Persistir metadados e corpo em object storage.
3. Processar anexos em worker isolado.
4. Adicionar regras de roteamento para tenant/mailbox.
5. Só depois adicionar IMAP/JMAP/webmail.

### Fase 5 — caixas profissionais

1. Subir Stalwart ou Mailcow isolado, preferencialmente em VPS separado.
2. Usar `mail.mago-bot.com` para SMTP/IMAP/JMAP/webmail.
3. Control-plane cria domínios e contas via API administrativa.
4. Guardar somente referências de conta e segredos cifrados.
5. Criar backup independente de volumes e mensagens.

### Fase 6 — produto comercial

1. Planos com mensagens, caixas, armazenamento e quotas.
2. Medição por `UsageLedgerEntry`.
3. limites de envio por domínio e tenant;
4. billing e overage;
5. painel de reputação;
6. documentação pública e SDKs;
7. sandbox com domínios de teste;
8. política antiabuso e revisão de contas.

## 10. Critérios de aceite

O recurso só deve ser considerado pronto quando:

- o worker estiver ativo e com heartbeat;
- um domínio puder ser cadastrado e verificado;
- SPF, DKIM, DMARC e MX forem exibidos com estado;
- um e-mail de teste retornar `202` e depois `delivered`;
- um bounce criar suppression;
- o mesmo webhook não duplicar evento;
- uma API key sem `mail.send` receber `403`;
- tenant A não conseguir usar remetente do tenant B;
- owner conseguir revogar provider, domínio e API key;
- inbound chegar ao tenant correto;
- anexos forem armazenados fora do PostgreSQL;
- nenhum segredo aparecer no painel, HTML, log ou resposta de API;
- o CRM e a Evolution continuarem saudáveis durante o rollout;
- backup e restauração forem testados.

## 11. Decisão recomendada

Para o estado atual, a sequência correta é:

1. **Não instalar ainda um servidor de e-mail dentro do CRM.**
2. Ativar e corrigir o worker transacional existente.
3. Implementar domínios, DNS, Cloudflare, API keys e painel no control-plane.
4. Usar Resend inicialmente para entrega e inbound webhook.
5. Criar uma camada de provider para permitir SES/Mailgun/Postmark depois.
6. Adicionar Stalwart ou Mailcow separado para caixas profissionais e IMAP/JMAP.
7. Manter `evo-api.mago-bot.com` intacto e expor a camada nova em `api.mago-bot.com`.

Essa abordagem aproveita o código já existente, reduz o risco de quebrar o CRM e deixa a plataforma preparada para vender API de e-mail sem confundir “envio transacional” com “hospedagem de caixas”.

## Fontes

1. [Resend — Managing Domains](https://resend.com/docs/dashboard/domains/introduction)
2. [Resend — Webhook Event Types](https://resend.com/docs/webhooks/event-types)
3. [Resend — Receiving Emails](https://resend.com/docs/knowledge-base/how-can-i-receive-emails-with-resend)
4. [Mailgun — Messages API](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/messages)
5. [Mailgun — Domains API](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/domains)
6. [Mailgun — Events API](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/events/get-v3-domain_name-events)
7. [Postmark — Servers API](https://postmarkapp.com/developer/api/servers-api)
8. [Postmark — Webhooks](https://postmarkapp.com/developer/webhooks/webhooks-overview)
9. [Amazon SES — Configuration Sets](https://docs.aws.amazon.com/ses/latest/dg/using-configuration-sets.html)
10. [Amazon SES — Event Destinations](https://docs.aws.amazon.com/ses/latest/dg/event-destinations-manage.html)
11. [Mailcow — Documentation](https://docs.mailcow.email/)
12. [Stalwart — Mail Server](https://www.stalwart.email/mail-server/)
13. [Stalwart — Management API](https://stalw.art/docs/development/api/)
14. [Cloudflare — Create API Token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
15. [Cloudflare — API Token Permissions](https://developers.cloudflare.com/fundamentals/api/reference/permissions/)
16. [Cloudflare — Cloudflare for SaaS](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/)
17. [Evolution Foundation](https://evolutionfoundation.com.br/)

