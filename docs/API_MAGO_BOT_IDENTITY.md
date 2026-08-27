# API Mago Bot — Identidade, superfícies e arquitetura

**Produto:** API Mago Bot — Produto de API
**Repositório:** `aryperdomo123456789-web/appapiwppmago`
**Atualizado:** 27 de agosto de 2026
**Autor:** Manus AI

> Este documento é a fonte de verdade de identidade do projeto. Ele evita a confusão entre o produto API Mago Bot e o produto CRM Mago Bot.

## 1. Mapa oficial dos produtos

| Produto | Repositório | Área de dono | Área de usuário | Escopo desta documentação |
|---|---|---|---|---|
| **API Mago Bot — Produto de API** | `appapiwppmago` | https://evo-api.mago-bot.com | https://app.mago-bot.com | **Sim** |
| **Mago Bot CRM** | `project-hello` | https://mago-bot.com/owner/login | https://mago-bot.com | **Não** |

O CRM não deve ser usado como origem de telas, sessão, banco, workers ou provider da API. Os dois produtos podem compartilhar marca comercial, mas possuem responsabilidades, runtimes e ciclos de deploy diferentes.

## 2. O que é a API Mago Bot

A API Mago Bot é um control plane e gateway multi-tenant para mensageria, conversas, automações e operação de canais. Ela oferece uma superfície estável para o cliente integrar organizações, projetos, API keys, scopes, quotas, idempotência, webhooks, inbox, auditoria e observabilidade.

A API Mago Bot não é a API oficial da Meta. **Meta Cloud** é o provider oficial quando configurado pelo cliente. **Evolution** é uma camada de compatibilidade premium para pilotos e operações opt-in. A experiência pode ser unificada no produto, mas as garantias, políticas, capabilities e semântica permanecem separadas.

## 3. Superfícies e permissões

| Superfície | Host | Público principal | Responsabilidade |
|---|---|---|---|
| Operations Console | `evo-api.mago-bot.com` | Owner, superadmin, operator e suporte permitido | Provisionamento, RBAC, MFA, providers, auditoria e operação |
| Portal customer-scoped | `app.mago-bot.com` | Usuários com membership | Organização, projeto, onboarding, canais, inbox, API keys e webhooks |
| API de produto | `app.mago-bot.com/v1/*` | Integradores com sessão ou API key | Contrato de integração e recursos tenant-scoped |
| Evolution provider | Interno | Apenas adapters do servidor | Sessões, QR/pairing, health e eventos de compatibilidade |
| Meta Cloud provider | Server-side | Adapter oficial configurado | WABA, Phone Number ID, templates e webhooks Meta |
| Manager bruto Evolution | Não público | Nenhum cliente | Bloqueado externamente; não faz parte do produto |

A conta **owner** tem wildcard administrativo, mas não é bypass. Ela usa sessão revogável, hostname correto, MFA para mutations críticas e auditoria. Usuários de cliente possuem somente memberships e scopes explícitos; não entram na Operations Console.

## 4. Caminho do primeiro valor

O cliente deve criar ou receber acesso a uma organização, selecionar um projeto, escolher conscientemente Meta Cloud ou Evolution, conectar um canal compatível, configurar a fila, receber o primeiro evento, visualizar a conversa no inbox e responder com idempotência. Um canal Evolution não deve ser apresentado como conexão oficial Meta.

A criação administrativa de tenant/projeto ocorre na Operations Console e exige MFA owner. A operação do cliente ocorre no portal customer-scoped. A API key de projeto é exibida uma única vez e nunca deve ser publicada no chat, frontend, URL ou log.

## 5. Organização do código

| Caminho | Função |
|---|---|
| `service/app/main.py` | Entry point FastAPI, metadata OpenAPI, assets e routers |
| `service/app/routes/ops_ui.py` | HTML da Operations Console |
| `service/app/assets/ops-app.js` / `ops.css` | Controller e design system owner |
| `service/app/routes/platform_ui.py` | HTML do portal usuário |
| `service/app/assets/platform-app.js` / `platform.css` | Portal customer-scoped e design system usuário |
| `service/app/routes/product_facade.py` | Fachada pública de produto |
| `service/app/routes/onboarding.py` | Checklist de primeiro valor |
| `service/app/routes/channels_public.py` | Lifecycle de canais customer-scoped |
| `service/app/routes/inbox.py` | Filas, assignment e timeline |
| `service/app/routes/mfa.py` | Enrollment e confirmação TOTP |
| `service/app/providers/meta_cloud.py` | Provider oficial Meta Cloud |
| `service/app/providers/evolution.py` | Provider Evolution compatibilidade |
| `service/app/providers/evolution_management.py` | Management adapter Evolution API v2/Evolution Go flavor |
| `service/sql/migrations/` | Schema versionado da API |
| `docs/` | Contratos, runbooks, prontidão e decisões |

## 6. Deploy e arquivos no servidor

O projeto de produção fica em `/opt/mago-platform`. O Docker Compose constrói os serviços e o Nginx aaPanel encaminha os hosts para as portas internas. O diretório `/www/wwwroot/app.mago-bot.com` pode permanecer vazio: ele é um webroot cadastrado pelo painel, não a origem privada do serviço.

O CRM possui outro runtime e não deve receber os arquivos da API. Uma promoção da API deve sincronizar somente o bundle fechado, manter envs e volumes, aplicar migrations autorizadas, reconstruir serviços afetados, testar healthchecks e preservar rollback de código.

## 7. Vocabulário oficial

Use sempre **API Mago Bot**, **Produto de API**, **Operations Console**, **Portal customer-scoped**, **Meta Cloud oficial** e **Evolution compatibilidade**. Use **API keys** para credenciais de integração de projeto. Use **licenças legadas** somente para as rotas antigas de licensing.

Evite usar como nome principal: `Mago Bot Platform`, `WhatsApp API Licensing`, `WebPlayer`, `IPTV`, `API oficial do WhatsApp` ou `Evolution oficial`. Esses termos podem aparecer apenas em contexto histórico, técnico ou de compatibilidade explicitamente explicado.

## 8. Critério de produto vendável

O produto está apto para piloto controlado quando um tenant pode ser provisionado com auditoria, um projeto pode emitir API key, um provider pode ser escolhido explicitamente, um canal pode ser conectado, mensagens/webhooks aparecem com tenant correto e o inbox permite operar o atendimento. Para GA enterprise ainda são necessários Embedded Signup Meta, billing operacional, SDKs, templates/interativos completos, status page, política de suporte/SLA e E2E real com número controlado.

## Referências

[1]: https://evo-api.mago-bot.com "API Mago Bot — Operations Console"
[2]: https://app.mago-bot.com "API Mago Bot — Portal customer-scoped"
[3]: https://github.com/aryperdomo123456789-web/appapiwppmago "API Mago Bot — Repositório"
[4]: https://github.com/aryperdomo123456789-web/project-hello "Mago Bot CRM — Repositório separado"
