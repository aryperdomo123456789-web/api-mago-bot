# Mago Bot — Inbox mínimo e primeiro valor

**Status:** implementado e validado no canário
**Escopo:** onboarding, canais Evolution customer-scoped, conversas e distribuição operacional.

## Objetivo

O pacote de primeiro valor reduz o caminho entre cadastro e primeira operação útil. Uma organização deve conseguir iniciar um projeto, conectar um canal Evolution de laboratório, acompanhar o estado do canal, receber uma conversa, consultar a timeline e distribuir o atendimento sem acesso a SSH, SQL manual ou credenciais do provider no navegador.

Evolution é um provider de compatibilidade premium. Meta Cloud é o provider oficial. Os dois usam o contrato Mago, mas possuem adapters, credenciais, estados, limites e semânticas separadas.

## Superfícies

A API pública de produto vive no domínio cliente e usa UUIDs públicos. A Operations Console permanece no domínio operacional. O inbox de sessão é exposto em `/v1/platform/inbox`; ele exige sessão válida e membership ativa. Rotas de outro hostname devem responder 404 para não revelar a existência do recurso.

## Estados de conversa e assignment

A conversa mantém o status de negócio (`active`, `waiting`, `handoff`, `closed` ou `archived`). O assignment possui estado próprio: `unassigned`, `assigned`, `claimed`, `queued`, `snoozed` ou `resolved`. Um assignment por conversa é garantido no banco. Claim usa lock pessimista para evitar dois agentes assumirem a mesma conversa simultaneamente.

## Rotas do inbox

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/v1/platform/inbox/queues` | Lista filas ativas do tenant, opcionalmente por projeto |
| POST | `/v1/platform/inbox/queues` | Cria uma fila com estratégia manual ou round-robin |
| GET | `/v1/platform/inbox/conversations` | Lista conversas com filtros de status, fila, agente e state |
| GET | `/v1/platform/inbox/conversations/{conversation_id}` | Retorna conversa, customer summary, assignment e timeline |
| POST | `/v1/platform/inbox/conversations/{conversation_id}/claim` | Assume a conversa para o agente da sessão |
| POST | `/v1/platform/inbox/conversations/{conversation_id}/assign` | Atribui fila e/ou agente pertencentes ao tenant |
| POST | `/v1/platform/inbox/conversations/{conversation_id}/release` | Libera o agente mantendo a fila quando configurada |
| POST | `/v1/platform/inbox/conversations/{conversation_id}/snooze` | Coloca a conversa em espera até timestamp futuro |
| POST | `/v1/platform/inbox/conversations/{conversation_id}/resolve` | Fecha conversa e marca assignment resolvido |
| POST | `/v1/platform/inbox/conversations/{conversation_id}/reopen` | Reabre conversa e retorna para unassigned |
| POST | `/v1/platform/inbox/conversations/{conversation_id}/notes` | Registra nota interna auditável |

Todas as operações verificam tenant e membership no servidor. UUID inexistente ou pertencente a outra organização deve responder 404; ausência de permissão deve responder 403 conforme o helper RBAC. Nenhuma resposta serializa token Evolution, segredo de webhook ou ID de provider.

## Segurança e auditoria

A migration `0010_inbox_distribution.sql` cria `inbox_queues` e `conversation_assignments`, com foreign keys para tenant, projeto, conversa, usuário e fila. Ações de criação, claim, assignment, release, snooze, resolve, reopen e note geram `AuditEvent` append-only com actor, request ID, IP, user-agent e metadata sanitizada.

O inbox não chama o provider diretamente. A resposta ao cliente continua usando o contrato de mensagens com API key, scope e `Idempotency-Key`; o composer visual é um próximo fechamento e não deve criar um segundo pipeline de envio.

## Primeiro valor

O teste mínimo de laboratório deve criar dois tenants, dois projetos e dois usuários. O tenant A conecta um canal fake/Evolution de laboratório, recebe evento inbound, lista a conversa, cria fila, faz claim, atribui agente, registra nota, coloca em snooze, resolve e reabre. O tenant B deve receber 404 ou 403 ao tentar acessar a conversa, fila ou assignment de A. Nenhuma etapa deve aceitar ID sequencial de outro tenant como substituto de UUID público.

## Operação

Antes de produção, aplicar a migration em backup restaurável, confirmar que o app e os workers estão healthy e verificar `/health/ready`. O provider real não deve ser chamado nos testes automatizados; usar dry-run ou adapter fake. Em produção, testar primeiro uma instância de laboratório. Monitorar latency de listagem, erros 4xx/5xx, claims concorrentes, filas sem agente, snooze vencido e crescimento de assignments.

## Rollback

Rollback de código restaura os arquivos do app no backup da promoção e recria apenas o serviço do app. A migration é aditiva e não deve ser apagada em rollback de código. Se a feature for desativada, esconder as rotas da UI e bloquear novas mutações, preservando as tabelas para investigação. Nunca remover dados de conversations, assignments ou audit events durante rollback.

## Fora deste pacote

O composer visual que dispara mensagem outbound pelo provider, tickets, SLA por fila, macros, sequences, flows versionados, CRM, billing checkout, RAG, copilot, CSAT, ROI e status page comercial ficam fora do primeiro corte. Eles devem reutilizar o mesmo Conversation Core, outbox, usage ledger, API keys, tracing e RBAC.

## Definition of Done

O pacote só está pronto para venda ampla quando o E2E autenticado com dois tenants comprovar isolamento, claim concorrente, webhook duplicado, retry, reconexão, mídia, erro normalizado, health e rollback. O canário atual comprova contrato, migration, autenticação de superfície e ausência de traceback; o teste com provider Evolution real de laboratório continua gate pendente.
