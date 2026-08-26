# Mago Bot — Estratégia de Produto com Dois Providers

**Objetivo:** construir um produto vendável de mensageria e automação, com experiência profissional inspirada em CPaaS maduras, sem copiar a Meta nem prometer garantias que o provider não possui.

## Definição do produto

O Mago Bot é um control plane de comunicação multi-tenant. Ele organiza clientes, projetos, recursos, chaves, quotas, mensagens, conversas, webhooks, auditoria, observabilidade e cobrança em uma única experiência. A conexão de WhatsApp é um detalhe de infraestrutura encapsulado por adapters.

O cliente compra uma experiência previsível do Mago: uma API estável, documentação clara, painel operacional, métricas, segurança, suporte e capacidade de trocar de provider sem reescrever a própria integração.

## Duas camadas, uma experiência

| Camada | Provider | Posicionamento | Garantias reais |
|---|---|---|---|
| **Oficial** | Meta WhatsApp Cloud API | Recomendado para produção crítica, escala e operação empresarial | Regras, templates, WABA, números e limites da Meta |
| **Compatibilidade premium** | Evolution API / Evolution Go | Entrada rápida, piloto e operação opt-in controlada | Dependência de sessão, estabilidade e políticas do provider |

As duas camadas compartilham o contrato Mago, Conversation Core, usage ledger, webhooks downstream, auditoria e tracing. Elas não compartilham o modelo de credenciais nem a promessa comercial.

## Contrato unificado

O cliente deve chamar o Mago, e não os endpoints internos da Evolution ou da Meta. O contrato mínimo é:

```text
project → resource → provider → message/conversation → webhook/status → usage/audit
```

Cada `resource` declara o provider, o estado, a capacidade e as limitações do plano. Uma mensagem deve retornar um identificador Mago e, quando existir, o identificador do provider. Erros precisam ter código estável, indicação de retry e request/trace ID.

## Segurança e eficiência como produto

A camada profissional não é apenas uma lista de endpoints. Ela precisa proteger o cliente contra erro operacional. Chaves ficam server-side ou cifradas; API keys são scoped por projeto; webhooks são HTTPS, assinados, deduplicados e protegidos contra SSRF; QR e pairing expiram; logs não carregam tokens; quotas e circuit breakers isolam tenants; e o healthcheck diferencia provider configurado de instância realmente conectada.

A eficiência vem de outbox, idempotência, fila por recurso, backpressure, retries classificados, cache de estado, upload de mídia por URL assinada e observabilidade de latência, erro e custo. O Mago não deve reconectar uma sessão em loop nem repetir uma mensagem comercial por causa de um retry mal classificado.

## Oferta comercial realista

| Plano | Provider | Perfil | Limite e promessa |
|---|---|---|---|
| **Starter** | Evolution compatibilidade | Teste e operação opt-in pequena | Conexão assistida, quotas baixas, sem SLA de sessão |
| **Pro** | Meta Cloud prioritária ou Evolution premium | Pequenas operações e automações | Webhooks, mídia, auditoria, suporte e limites claros |
| **Enterprise** | Meta Cloud | Operação crítica e parceiros | Onboarding oficial, governança, SLA contratado e suporte de migração |

A Evolution não deve ser usada para spam, listas compradas, disparo frio ou volume agressivo. O produto deve bloquear ou revisar padrões de abuso, registrar consentimento e fornecer opt-out por projeto.

## O que está pronto e o que é gate

A fundação do control plane, multi-tenancy, RBAC, API keys, quotas, idempotência, Conversation Core, webhooks, tracing, Operations Console, e-mail transacional e a camada gerenciada Evolution já existem no branch de trabalho. O pacote Evolution foi validado no canário com migration, lifecycle, webhook, mídia, health worker e documentação.

O próximo gate de produto é um teste E2E autenticado em uma instância Evolution de laboratório. Depois dele, a promoção exige backup, callback público, proxy central, migration em produção e rollout controlado. Para a camada oficial, o gate separado é Meta Cloud configurada e onboarding Embedded Signup por cliente.

## Métricas de qualidade

O produto deve acompanhar ativação de primeiro resource, tempo até conexão, taxa de conexão, disponibilidade por provider, mensagens aceitas, entregas, falhas por categoria, retries, latência p95, eventos duplicados, webhooks entregues, instâncias degradadas, incidentes por tenant e custo por mensagem. A meta não é parecer grande; é saber exatamente onde o sistema falha.

## Fora de escopo do posicionamento

O Mago não deve afirmar ser Meta, BSP oficial, WhatsApp Cloud API ou garantia contra bloqueio quando o cliente usa Evolution. Também não deve esconder a diferença entre um remetente configurado e uma sessão conectada, nem liberar o Manager bruto como se fosse uma interface do produto.

## Critério de sucesso

O Mago será considerado vendável quando um cliente conseguir criar projeto, escolher provider compatível com o plano, conectar um resource por fluxo guiado, enviar/receber mensagens pelo contrato único, configurar webhook, consultar status, acompanhar uso, revogar acesso e encontrar documentação e suporte sem depender de entrar no container. O produto será considerado pronto para escala empresarial somente quando a camada Meta Cloud cumprir seus próprios gates de onboarding, compliance, qualidade e SLA.
