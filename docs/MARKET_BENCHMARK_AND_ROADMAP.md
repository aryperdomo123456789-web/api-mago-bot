# Mago Bot — Benchmark de mercado e roadmap de produto

**Data da pesquisa:** 2026-08-26
**Objetivo:** definir um produto vendável, seguro e eficiente inspirado em padrões públicos de CPaaS e atendimento, sem copiar código ou prometer equivalência à Meta.

## Tese do produto

O Mago Bot deve ser um **control plane de comunicação multi-tenant**, e não apenas um endpoint para mandar mensagens. O valor comercial está em tornar uma conexão complexa previsível: onboarding guiado, resources/senders, contrato de API estável, webhooks e status, quotas, auditoria, suporte e operação.

A experiência é única, mas os providers são explicitamente diferentes:

| Camada | Provider | Promessa comercial |
|---|---|---|
| Oficial | Meta WhatsApp Cloud API | WABA, números comerciais, templates, regras e limites oficiais da Meta |
| Compatibilidade premium | Evolution API / Evolution Go | Lifecycle gerenciado, API Mago unificada e operação opt-in sujeita à estabilidade da sessão |

O Mago não copia a Meta. Ele oferece uma camada de abstração, governança e operação que permite ao cliente escolher o provider adequado ao seu estágio e migrar sem reescrever a integração.

## Padrões públicos de mercado

Twilio reúne sender, onboarding, webhook inbound, status de saída, mídia, templates, Conversations, Console e fallback operacional em uma experiência coerente.[1] A 360dialog separa onboarding em Direct Link, Connect Button, Custom IO e Partner-hosted Embedded Signup, além de distinguir webhooks de lifecycle dos webhooks de mensageria.[2] A respond.io evidencia que o produto vendável também inclui Organization/Workspace, inbox de equipe, workflows, reports, API, webhooks, 2FA, SSO, uso por contatos e créditos de IA.[3] O Evolution Go mostra que, no provider de compatibilidade, lifecycle de instância, QR/pairing, mídia, eventos e storage são os primitives que precisam ser encapsulados.[4]

## Comparação com o estado do Mago

| Domínio | Padrão de mercado | Mago atual | Gap principal |
|---|---|---|---|
| Control plane | Organização, workspace, subcontas, tenants e recursos | Multi-tenant, projetos, API keys, quotas, RBAC e Operations Console | Refinar workspace/seats e entitlements por plano |
| Onboarding | Self-service, Embedded Signup, wizard e checklist | Evolution lifecycle gerenciado e Meta manual/assistida | Wizard comercial, teste guiado e Meta Embedded Signup |
| Sender/instância | Catálogo com estado, saúde, qualidade e owner | `EvolutionInstance` com lifecycle, status e health worker | Capacidade/qualidade por resource e UX E2E autenticada |
| Mensagens | Texto, mídia, templates, interativos e status | Contrato Mago com texto/mídia, idempotência e provider adapters | Fechar interativos, templates e normalização de status por provider |
| Webhooks | Inbound, outbound status, retry, fallback e replay | Webhook Evolution secreto, dedupe, outbox e downstream delivery | Fallback configurável, replay UI e contrato de eventos publicado |
| Conversas | Inbox, histórico, contatos, handoff e workflows | Conversation Core, timeline e portal base | Team inbox, agentes, assignment e automações visuais |
| Segurança | API keys scoped, 2FA/SSO, isolamento e masking | RBAC, sessões revogáveis, MFA scaffolding, SSRF hardening e redaction | MFA obrigatório por política, SSO enterprise e masking de PII |
| Operação | Dashboards, insights, status page e suporte/SLA | Tracing, filas, alertas, usage ledger e diagnóstico | SLO/SLA, status page, runbooks e relatórios para cliente |
| Comercial | Assinatura + uso, contatos ativos, seats, channel fees e suporte | Planos, trials, licenças e quotas | Billing recorrente, excedente previsível e medição por provider |
| SDK/docs | API docs por linguagem, exemplos e Postman | OpenAPI e documentação de provider | SDKs TypeScript/Python, quickstarts e sandbox |
| Dados/mídia | Storage gerenciado, retenção e exportação | Mídia aceita no adapter; storage recomendado | S3/MinIO assinado, TTL, retenção, exportação e limpeza |

## Produto mínimo vendável

O primeiro produto vendável não precisa de todos os módulos de uma Twilio. Ele precisa fechar uma jornada inteira sem operação manual escondida:

1. O cliente cria conta, projeto e resource.
2. O sistema explica a diferença entre Meta oficial e Evolution compatibilidade.
3. O cliente conecta uma instância de laboratório ou inicia Meta onboarding conforme o plano.
4. A central mostra estado real, saúde, QR/pairing, erros e próximo passo.
5. O cliente envia texto e mídia pelo contrato Mago usando API key scoped e idempotência.
6. Mensagens recebidas, status e falhas chegam no Conversation Core e nos webhooks assinados.
7. O cliente consulta uso, quotas, eventos, logs redacted e auditoria sem entrar no servidor.
8. O produto bloqueia abuso, respeita opt-out e permite revogar resource/key.
9. Suporte consegue operar, fazer replay e recuperar uma instância sem apagar dados.

## Roadmap por prioridade

### P0 — fechar a jornada Evolution premium

O P0 é o pacote que transforma código em produto: wizard de onboarding, resource catalog, estados e health reais, webhook/fallback/replay, mídia via storage assinado, códigos de erro públicos, documentação quickstart e teste E2E de laboratório. Sem esse pacote, a camada é tecnicamente interessante, porém ainda depende de intervenção de engenharia.

### P1 — confiança comercial

O P1 adiciona billing recorrente e usage-based, entitlements por plano, alertas de quota, SLOs, status page, runbooks, suporte, MFA obrigatório para operadores, exportação e retenção de dados, SDKs e exemplos executáveis. É aqui que o cliente deixa de comprar uma instalação e passa a comprar um serviço.

### P2 — diferenciação

O P2 pode trazer team inbox, assignment de agentes, workflows, handoff humano, templates e interativos quando suportados pelo provider, AI Gateway com roteamento controlado, transcrição de áudio, resumos, RAG por tenant, avaliações e automações. IA entra depois do caminho de mensagem estar observável e idempotente; colocar um modelo antes disso é enfeite caro.

## Regras de segurança e eficiência

Toda chamada externa precisa de timeout, classificação de erro, retry apenas quando seguro, circuit breaker, request/trace ID e métrica. Toda entrada de webhook precisa de autenticação, limite de tamanho, dedupe, redaction e processamento assíncrono. Toda mídia precisa de allowlist MIME, limite, antivírus quando aplicável, URL assinada e TTL. Toda credencial deve ser server-side/cifrada e nunca aparecer em HTML, OpenAPI, log ou webhook downstream.

A Evolution deve ter limites inferiores e avisos explícitos por plano. O Mago não pode vender volume frio, lista comprada ou garantia contra bloqueio. O sistema deve registrar consentimento e opt-out; a qualidade da sessão é responsabilidade compartilhada com o cliente e o provider.

## Critérios de prontidão

| Gate | Critério de aceite |
|---|---|
| Piloto assistido | Uma instância de laboratório conecta, envia/recebe texto e mídia e recupera após desconexão |
| Beta vendável | Wizard, resource catalog, webhook/replay, quotas, docs, suporte e cobrança de teste funcionam ponta a ponta |
| Produção profissional | SLO, backup/restore, status page, MFA obrigatório, carga, incident response e migração de provider validados |
| Enterprise | Meta Cloud onboarding, governança, SLA contratado, isolamento forte, SSO e auditoria/exportação compatíveis com o contrato |

## Decisão

O Mago deve competir por **clareza, governança e velocidade de integração**, não por fingir ser a Meta. A Evolution é a porta de entrada para pilotos e operações opt-in; a Meta Cloud é o caminho oficial para produção crítica. O núcleo comum deve proteger o cliente das diferenças, mas nunca escondê-las.

## References

[1]: https://www.twilio.com/docs/whatsapp/api "Twilio — WhatsApp Business Platform API"

[2]: https://docs.360dialog.com/partner/onboarding/integrated-onboarding "360dialog — Integrated Onboarding"

[3]: https://respond.io/pricing "respond.io — Pricing and feature tiers"

[4]: https://docs.evolutionfoundation.com.br/evolution-go "Evolution Go — documentação oficial"
