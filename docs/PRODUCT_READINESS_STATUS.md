# Mago Bot — Estado de prontidão do produto

**Data:** 26 de agosto de 2026
**Autor:** Manus AI
**Escopo:** plataforma/API WhatsApp multi-tenant, com Meta Cloud oficial e Evolution como provider de compatibilidade premium.

## Resumo executivo

O Mago Bot já possui uma fundação operacional real em produção, com control plane multi-tenant, RBAC, sessões revogáveis, API keys e scopes, quotas, idempotência, webhooks/outbox, workers, tracing, rate limit/circuit breaker, auditoria append-only, healthchecks e isolamento por hostname.

O pacote Primeiro Valor foi promovido e validado em produção. Ele inclui lifecycle Evolution gerenciado, canais customer-scoped, onboarding de primeiro valor, inbox mínimo, filas e distribuição, além do worker de health da Evolution. Meta Cloud permanece um adapter separado e é a camada oficial; Evolution não deve ser descrita como API oficial da Meta.

A conta owner agora possui contrato wildcard: recebe os privilégios customer-scoped sobre tenants ativos e poderes administrativos adicionais para provisionar tenant, membership, assinatura, projeto e fila inicial. O endpoint owner-only de provisionamento exige MFA habilitado. Esse gate permanece pendente porque o owner ainda não concluiu o enrollment no autenticador.

## O que foi validado

| Área | Estado | Evidência | Limite honesto |
|---|---|---|---|
| Runtime de produção | Validado | App, webhook worker, owner-welcome worker, Evolution health worker e bancos essenciais saudáveis | Não houve teste com número real nesta etapa |
| Migrations Primeiro Valor | Validado | 0008, 0009 e 0010 aplicadas no PostgreSQL de plataforma; tabelas confirmadas | Migration 0007/Resend não foi promovida |
| Evolution | Validado em contrato e superfície | Lifecycle, onboarding, webhook, health worker e provider separado presentes | Ainda não há entrega real autenticada neste ciclo |
| Owner wildcard | Validado no canário e promovido | RBAC, fachada customer-scoped, endpoint owner-only e UI MFA | Provisionamento aguarda MFA |
| Meta Cloud | Estruturalmente separado | Adapter e superfície administrativa preservados | Sem credenciais Meta e sem teste de envio |
| Operations Console | Recuperado | Overview autenticado volta a HTTP 200 e exibe métricas | A faixa de erro antiga pode permanecer visualmente até hotfix de limpeza de estado |
| Resend | Degradação segura | Métricas de e-mail retornam zero quando `email_deliveries` não existe | Nenhum segredo ou worker Resend foi promovido |
| Segurança | Parcialmente validada | Segredos não aparecem na UI/OpenAPI; Manager continua bloqueado | MFA owner ainda é gate pendente |

## Gating atual

O próximo desbloqueio operacional é concluir o MFA do owner diretamente na Operations Console. O segredo TOTP, QR/URI e códigos de recuperação devem permanecer exclusivamente com o proprietário. Após o card mudar para **MFA Ativo**, o owner poderá provisionar o tenant e o projeto do laboratório pela tela **Clientes / Tenants**, sem escrita direta no banco.

O número exclusivo de laboratório deve ser conectado somente depois do provisionamento. O teste será limitado a QR/pairing, status connected, webhook, uma mensagem inbound opt-in, uma conversa tenant-scoped, claim/assignment, uma resposta controlada e auditoria. Não há autorização para disparos em massa ou para substituir o número de produção antes da estabilização.

## Definição de produto vendável

O Mago Bot pode ser apresentado como uma plataforma CPaaS multi-tenant com duas camadas explicitamente diferentes. A camada Meta Cloud é oficial e deve receber credenciais, templates e políticas próprias. A camada Evolution é uma compatibilidade premium para operações controladas, com lifecycle gerenciado, webhooks, health, inbox e observabilidade, mas com limites de estabilidade, dependência de sessão e política do WhatsApp que precisam aparecer na documentação comercial.

A prontidão comercial não deve ser confundida com prontidão de escala ilimitada. Ainda faltam MFA owner concluído, E2E autenticado com número de laboratório, teste de restore isolado, alertas operacionais observados em produção, contrato de billing efetivo e política de suporte/SLA. Esses itens permanecem no roadmap, não são considerados entregues por inferência.
