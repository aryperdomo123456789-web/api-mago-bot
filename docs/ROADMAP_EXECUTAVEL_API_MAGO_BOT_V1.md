# Roadmap executável — API Mago Bot v1

**Escopo:** API Mago Bot em `app.mago-bot.com`, separada do CRM `mago-bot.com`.

**Objetivo:** transformar a fundação alpha em um piloto privado vendável de canais WhatsApp, com contrato público estável, evidência E2E, recuperação comprovada e operação segura.

> Este documento não declara capacidades prontas. Cada bloco só pode ser marcado como concluído após evidência versionada, teste repetível e critério de aceite atendido.

## Princípios de execução

A Evolution API é tratada como provider de compatibilidade baseado em sessão; Meta Cloud permanece um adapter oficial separado. O contrato público usa `project_uuid`, `channel_uuid`, operações persistentes, idempotência, scopes, webhooks assinados e envelopes de erro. O CRM não compartilha banco, sessão, cookies, rotas administrativas ou credenciais com a API Mago Bot.

Toda mudança de runtime segue o fluxo **local → canário isolado → backup → gates → produção autorizada**. Nenhuma mutation deve incluir segredo em commit, log, HTML, resposta ou relatório. Migrations são forward-only e restauração destrutiva em produção é proibida.

## Gate P0-01 — Estado confiável do canal

**Problema:** o provider Evolution pode responder `open` enquanto o control plane registra `degraded`.

**Entrega:** máquina de estados canônica, reconciliação periódica, timeout de conexão, registro de causa, `last_seen`, transições idempotentes e alertas para divergência.

**Aceite:** provider, worker e control plane convergem para o mesmo estado; uma conexão não confirmada não é anunciada como saudável; reconexão não duplica operação; QR expirado retorna estado e erro normalizados.

**Dependência externa:** escaneamento de QR em número de laboratório e confirmação visual do vínculo.

## Gate P0-02 — Suíte E2E e segurança

**Entrega:** banco/Redis de testes separados e guard contra produção; testes de signup, confirmação, MFA, RBAC, isolamento cross-tenant, API key/scopes, canal, QR, conexão, webhook duplicado, HMAC, retries, idempotência, mídia e desconexão.

**Aceite:** tenant A não acessa projeto, canal, conversa, integração, webhook ou billing de tenant B; mutations repetidas não duplicam operação; assinatura inválida é rejeitada; retry controlado chega à dead letter quando excede a política.

## Gate P0-03 — Backup e restore isolado

**Entrega:** backup PostgreSQL da plataforma, PostgreSQL Evolution, Redis necessário e volumes persistentes de sessão; manifesto de versão, checksum, retenção e procedimento de restauração em ambiente separado.

**Aceite:** restauração isolada inicia sem tocar produção; schema, canal e operações críticas são legíveis; sessão de laboratório e dados de control plane têm consistência documentada; relatório registra duração e limites.

## Gate P0-04 — Contenção e observabilidade

**Entrega:** limites Docker de CPU, memória e PIDs; healthchecks de PostgreSQL, Redis, Evolution e workers; métricas de latência, erros, filas, retries, circuito e estado por shard; alertas básicos e runbook.

**Aceite:** falha de Redis/Evolution aparece como `degraded` explicável; uma instância problemática não consome todos os recursos; readiness não declara pronto quando dependência crítica está indisponível.

## Gate P1-01 — Trial e onboarding

**Entrega:** trial de 7 dias com verificação de e-mail, limites, estado, expiração, convite, primeiro projeto, primeira chave, primeiro canal e sandbox. Boas-vindas por e-mail usam ativação segura; senha nunca é enviada em texto puro. WhatsApp exige opt-in explícito.

**Aceite:** novo usuário chega ao primeiro valor sem intervenção manual; trial expirado bloqueia operações com erro claro; reprocessamento não duplica welcome; falha de provider é observável e recuperável.

## Gate P1-02 — Billing mínimo

**Entrega:** selecionar um gateway antes da implementação final; checkout, assinatura, ativação, renovação, falha, suspensão e reconciliação de webhook. O produto não deve anunciar billing enquanto `checkout.available` for falso.

**Dependência externa:** decisão do proprietário entre Stripe, Mercado Pago ou Pagar.me e configuração segura das credenciais.

## Gate P1-03 — E-mail transacional

**Entrega:** provider adapter, domínio verificado, SPF/DKIM/DMARC, sender identities, API keys com `mail.send`, quotas, eventos, supressões, inbound webhook e dry-run. Caixas IMAP/JMAP são um produto separado e devem usar serviço isolado.

**Aceite:** envio retorna `202`, evento chega a `delivered`, bounce gera suppression, webhook é idempotente, corpo/anexos não vazam para logs e tenant não cruza remetente.

**Dependência externa:** chave Resend rotacionada e DNS do domínio configurado pelo proprietário.

## Gate P2-01 — Shards Evolution

**Entrega:** entidade `shard`, relação canal→provider→instância→shard, Instance Manager, quotas por shard, ownership único por sessão, volumes persistentes e roteamento por capacidade.

**Aceite:** segundo ambiente de laboratório opera sem tocar no canal atual; falha de um shard não corrompe os demais; cliente recebe apenas `channel_uuid`; capacidade e estado são auditáveis.

> Vários containers no mesmo host não constituem alta disponibilidade. Hosts separados, restore comprovado e métricas devem preceder qualquer promessa de SLA.

## Contrato mínimo do piloto vendável

Um cliente externo só deve ser admitido quando conseguir criar projeto, emitir API key restrita, criar canal, conectar número de laboratório, receber webhook HMAC, consultar operação, enviar uma mensagem com opt-in, repetir a requisição sem duplicar e consultar o estado final.

O posicionamento comercial deve ser **piloto privado de infraestrutura WhatsApp com adapters Meta Cloud e Evolution**, sem prometer equivalência oficial, escala ilimitada ou SLA enterprise antes dos gates P0 e P1.

## Dependências que exigem ação do proprietário

| Dependência | Ação necessária |
|---|---|
| QR e mensagens | Número de laboratório, opt-in e confirmação do destinatário |
| Billing | Escolher gateway e inserir credenciais no ambiente seguro |
| E-mail real | Revogar chaves expostas, configurar nova chave fora do chat e publicar DNS |
| Escala | Autorizar novos servidores/orçamento e política de capacidade |
| Produção | Autorizar cada promoção após evidência canária |

## Evidência obrigatória por entrega

Cada gate deve publicar documento sanitizado com commit, timestamp, ambiente, testes executados, resultado, limitações, arquivos alterados e rollback. O relatório não deve conter API key, token, QR, cookie, TOTP, HMAC secret, telefone completo, JID ou corpo de mensagem.

## Ordem recomendada

A ordem correta é P0-01, P0-02, P0-03 e P0-04; depois P1-01, P1-02 e P1-03; somente então P2-01. Adicionar providers de IA, marketplace ou telas cosméticas antes desses gates aumenta superfície sem aumentar confiança operacional.
