# E-mail transacional — Resend Free

**Produto:** Mago Bot Platform
**Estado:** implementado e validado no canário em dry-run
**Data:** 26 de agosto de 2026
**Autor:** Manus AI

## Objetivo

O Mago Bot envia e-mails transacionais de onboarding e autenticação usando identidades do domínio verificado, sem criar uma caixa de entrada. Os remetentes podem ser `contato@app.mago-bot.com`, `suporte@app.mago-bot.com`, `vendas@app.mago-bot.com` e outros aliases permitidos. O conteúdo informa que a mensagem é automática e não deve ser respondida.

A primeira versão usa o Resend Free atrás de um adapter próprio. A aplicação não chama o provider durante o request do usuário: a rota grava uma entrega pendente, e um worker assíncrono executa o envio, aplica retry e atualiza o estado. A integração pode ser trocada por Postmark, SES ou SMTP sem reescrever os fluxos de signup e autenticação.

## Fluxos cobertos

| Fluxo | Gatilho | Mensagem | Estado canário |
|---|---|---|---|
| Verificação | `POST /v1/platform/auth/signup` | Link de confirmação com token de uso único | Validado em dry-run |
| Boas-vindas | `POST /v1/platform/auth/verify-email` | Onboarding após confirmação do endereço | Implementado |
| Reset | `POST /v1/platform/auth/password-reset/request` | Link temporário de redefinição | Validado em dry-run |
| Entrega | `POST /v1/webhooks/email/resend` | Eventos assinados do provider | Assinatura e dedupe implementados |

Os links usam `https://app.mago-bot.com/admin`. O portal agora reconhece `?verify=...` e `?reset=...`, confirma o e-mail e conclui o reset sem expor o token em diagnóstico ou resposta de API.

## Modelo de dados

A migration `service/sql/migrations/0007_email_transacional.sql` cria:

- `email_sender_identities`: aliases de remetente, nome, `Reply-To`, status e escopo.
- `email_deliveries`: payload renderizado, estado, tentativas, horários, provider message ID e erro sanitizado.
- `email_suppressions`: destinatários que não devem mais receber mensagens após bounce ou complaint.
- `email_provider_events`: deduplicação de eventos Resend por `provider + svix-id`.

O índice único `(source_type, source_id, message_type)` evita duplicar verificação, boas-vindas ou reset para a mesma origem. Segredos do Resend não são persistidos no banco nesta primeira etapa; a API key fica apenas no ambiente do worker/app.

## Worker e resiliência

O módulo `service/app/email_worker.py` usa claim concorrente com `FOR UPDATE SKIP LOCKED`, heartbeat para Docker healthcheck, retry exponencial limitado, dead-letter e suppression antes do envio. O teto padrão é `RESEND_DAILY_LIMIT=100`, alinhado ao plano gratuito consultado; o budget é aplicado via rate limit persistente e não fica em memória.

O adapter `service/app/providers/resend_email.py` tem `RESEND_DRY_RUN=true` por padrão. Em dry-run nenhum request externo é feito; a entrega recebe um ID sintético `dryrun_...` e fica como `sent` para validar o pipeline. O envio real só ocorre quando `RESEND_DRY_RUN=false` e `RESEND_API_KEY` estiver configurado no ambiente seguro.

O webhook valida `svix-id`, `svix-timestamp` e `svix-signature`, rejeita clock skew superior a cinco minutos, persiste o evento antes de atualizar a entrega e deduplica reenvios. Eventos `email.bounced` e `email.complained` adicionam o destinatário à suppression list.

## Aliases no Operations Console

A aba **E-mail transacional** da Operations Console permite listar e criar remetentes dentro de `EMAIL_ALLOWED_SENDER_DOMAINS`, configurar nome e `Reply-To`, e desativar aliases. As mutações exigem papel `owner`, `platform_superadmin` ou `platform_operator` e geram `AuditEvent`. Papéis de cliente não acessam a rota.

Endpoints:

| Método | Endpoint | Política |
|---|---|---|
| `GET` | `/v1/ops/email/senders` | Operacional, sem segredos |
| `POST` | `/v1/ops/email/senders` | Mutação operacional, domínio allowlisted |
| `PATCH` | `/v1/ops/email/senders/{id}` | Mutação operacional |
| `DELETE` | `/v1/ops/email/senders/{id}` | Desativação auditada |
| `POST` | `/v1/webhooks/email/resend` | Público, somente assinatura Svix válida |

## Configuração segura

O template `service/deploy/service.env.example` documenta as variáveis:

```env
RESEND_API_KEY=CHANGE_ME_RESEND_API_KEY
RESEND_API_BASE_URL=https://api.resend.com
RESEND_DRY_RUN=true
RESEND_WEBHOOK_SIGNING_SECRET=CHANGE_ME_RESEND_WEBHOOK_SIGNING_SECRET
RESEND_DAILY_LIMIT=100
EMAIL_ALLOWED_SENDER_DOMAINS=app.mago-bot.com
EMAIL_DEFAULT_FROM=contato@app.mago-bot.com
EMAIL_DEFAULT_FROM_NAME=Mago Bot
EMAIL_DEFAULT_REPLY_TO=nao-responda@app.mago-bot.com
EMAIL_PUBLIC_BASE_URL=https://app.mago-bot.com
EMAIL_WORKER_POLL_SECONDS=2
EMAIL_WORKER_MAX_ATTEMPTS=8
EMAIL_WORKER_HEARTBEAT=/tmp/mago_email_worker_heartbeat
```

Esses valores são nomes e placeholders; nenhuma API key, signing secret ou credencial foi incluída no repositório. O canário funciona sem chave porque o default é dry-run.

## DNS e entregabilidade

Antes de ativar envio real, adicionar `app.mago-bot.com` ou um subdomínio dedicado no Resend e publicar exatamente os registros DNS fornecidos pela conta: SPF, DKIM, Return-Path e política DMARC. Recomenda-se separar a reputação transacional em um subdomínio como `mail.app.mago-bot.com` quando o domínio principal também for usado para outras finalidades.

A ativação real deve seguir esta ordem:

1. Verificar o domínio no Resend.
2. Publicar e confirmar SPF, DKIM e DMARC.
3. Criar o webhook HTTPS para `https://evo-api.mago-bot.com/v1/webhooks/email/resend` e guardar o signing secret no ambiente seguro.
4. Inserir `RESEND_API_KEY` no ambiente seguro do app e worker.
5. Manter `RESEND_DRY_RUN=true` até concluir um teste controlado.
6. Mudar para `RESEND_DRY_RUN=false`, reiniciar apenas app e worker após backup e executar um envio autorizado para uma caixa de teste.
7. Monitorar entregas, bounces, complaints e o limite diário antes de liberar onboarding geral.

O remetente e o `Reply-To` não criam caixas de entrada. Como o requisito é não receber respostas, o produto usa `nao-responda@app.mago-bot.com` e o rodapé informa que a mensagem é automática. Se no futuro for necessário receber respostas, será preciso configurar inbound/MX e uma camada adicional de triagem.

## Validação no canário

A validação foi feita sem envio real:

| Verificação | Resultado |
|---|---|
| Migration `0007_email_transacional` | Aplicada no banco canary |
| App canary | `healthy` |
| Email worker canary | `healthy` |
| Webhook worker canary | `healthy` |
| Owner welcome worker canary | `healthy` |
| Signup sintético | HTTP 201 |
| Verificação enfileirada | `email_verification | sent | dryrun_...` |
| Reset sintético | HTTP 200 |
| Reset enfileirado | `password_reset | sent | dryrun_...` |
| Rota operacional sem sessão | HTTP 401 |
| Webhook sem assinatura | HTTP 401 |
| Portal `/admin` | HTTP 200 |
| Cache do JS de auth | `/assets/platform-app.js?v=20260826-3` HTTP 200 |

O cadastro de teste foi feito apenas no banco canary e não gera mensagem externa.

## Gates de produção

A implementação está pronta para piloto controlado, mas **não deve enviar e-mail real automaticamente** enquanto o domínio não estiver verificado, a chave não estiver no secret manager e `RESEND_DRY_RUN` não for alterado conscientemente. A promoção futura para produção precisa incluir backup, migration 0007, novo worker `mago_email_worker`, configuração segura e um teste de caixa autorizado.

## Referências

[1]: https://resend.com/pricing "Resend Pricing"
[2]: https://resend.com/docs/dashboard/domains/introduction "Resend Domains"
[3]: https://resend.com/docs/webhooks/introduction "Resend Webhooks"
[4]: https://resend.com/docs/api-reference/emails/send-email "Resend Send Email API"
