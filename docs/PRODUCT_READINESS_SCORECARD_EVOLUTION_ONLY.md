# Mago Bot — Scorecard de prontidão com Evolution בלבד

**Data:** 2026-08-26
**Escopo:** comparação de produto com plataformas CPaaS e de atendimento; não é certificação nem promessa de equivalência à Meta.

## Nota geral

**Nota atual estimada: 5,5/10 contra os grandes players quando o produto usa somente Evolution.** Essa é uma estimativa de produto, não uma métrica oficial de mercado. A infraestrutura de control plane é mais madura do que a experiência comercial completa; por isso uma média simples esconde os gaps.

| Dimensão | Nota | Por que não é maior |
|---|---:|---|
| Control plane, multi-tenancy e RBAC | 7,5/10 | Tenant, projeto, resource, API keys, quotas, auditoria, sessões revogáveis e Operations Console existem; faltam workspaces/seats/SSO comerciais |
| Segurança e resiliência | 7/10 | Segredos server-side/cifrados, SSRF hardening, idempotência, rate limit, circuit breaker, tracing e healthchecks existem; MFA ainda precisa ser obrigatório e falta teste real de incident response |
| Lifecycle da Evolution | 6,5/10 | Create, connect, QR, pairing, status, reconnect, disconnect, logout, tombstone e health worker existem; teste E2E autenticado de laboratório ainda é gate |
| Mensageria e mídia | 5,5/10 | Texto e mídia foram normalizados; faltam interativos completos, storage assinado/TTL, validação operacional de mídia e cobertura E2E por tipo |
| Webhooks e status | 6/10 | Endpoint protegido, dedupe, state machine, outbox e downstream delivery existem; faltam fallback/replay visível, contrato completo de eventos e status page |
| Inbox, agentes e workflows | 3,5/10 | Conversation Core/timeline existem, mas team inbox, assignment, automações visuais e handoff humano ainda não são produto completo |
| Documentação e SDKs | 4/10 | OpenAPI e documentação de provider existem; faltam SDKs TypeScript/Python, quickstarts testados, Postman e exemplos por linguagem |
| Billing, planos e suporte | 3,5/10 | Planos, trials, licenças e quotas existem; falta billing recorrente, excedente previsível, SLO/SLA, status page e suporte com runbooks |
| Onboarding self-service | 4/10 | Lifecycle assistido existe; falta wizard completo, diagnóstico guiado, teste de conexão sem prompts e onboarding oficial por cliente |

## Como interpretar

A nota não significa que o código é fraco. Ela mostra que os players maduros vendem uma jornada inteira. Twilio combina sender, onboarding, templates, webhooks, status, fallback, mídia, Conversations e Console.[1] 360dialog expõe onboarding em Direct Link, Connect Button, Custom IO e Partner-hosted Embedded Signup, além de separar webhooks de lifecycle e mensageria.[2] respond.io adiciona workspace, inbox, workflows, reports, API, webhooks, 2FA/SSO e uso por contatos.[3]

Com o P0 completo — wizard, catálogo de resource, health real, replay/fallback, storage de mídia, erros públicos, quickstarts e E2E de laboratório — a estimativa de experiência da camada Evolution sobe para **7/10**. O produto passa a ser vendável como provider de compatibilidade premium para piloto e operação opt-in. P1 — billing, SLO, suporte, SDKs, status page e governança — pode levar a experiência para **8/10**.

Nenhuma dessas notas transforma Evolution em Meta Cloud. A documentação do Evolution Go descreve API REST, QR, mídia, eventos em tempo real e múltiplos transportes de eventos; o transporte continua sendo sessão WhatsApp Web e os limites de estabilidade/qualidade são próprios do provider.[4] Para o rótulo **oficial**, a camada Meta Cloud precisa continuar separada.

## P0 que vira código a seguir

1. Wizard visual de onboarding com validação, capability discovery e checklist de ativação.
2. Catálogo de instâncias por tenant/projeto, com filtros de estado, provider flavor, saúde e ações seguras.
3. Webhook delivery log com replay controlado, backoff, fallback e suspensão automática de destinos instáveis.
4. Upload de mídia por URL assinada/TTL ou política estrita de URL externa, com MIME/size allowlist.
5. Catálogo de erros e quickstarts executáveis em TypeScript, Python e cURL.
6. Testes E2E de laboratório e carga, sem tocar a instância ou o número de produção.

## References

[1]: https://www.twilio.com/docs/whatsapp/api "Twilio — WhatsApp Business Platform API"

[2]: https://docs.360dialog.com/partner/onboarding/integrated-onboarding "360dialog — Integrated Onboarding"

[3]: https://respond.io/pricing "respond.io — Pricing and feature tiers"

[4]: https://docs.evolutionfoundation.com.br/evolution-go "Evolution Go — documentação oficial"
