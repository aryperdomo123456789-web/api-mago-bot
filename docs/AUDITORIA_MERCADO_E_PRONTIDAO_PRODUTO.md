# Auditoria de mercado e prontidão do produto — Mago Bot

**Data:** 26 de agosto de 2026  
**Escopo:** comparação com Twilio e referências de WhatsApp/CPaaS; auditoria do código e da configuração Meta; diagnóstico de prontidão comercial.

## Veredito direto

O Mago Bot **já é uma fundação técnica séria de control plane/API multi-tenant**, com sessões server-side, RBAC, API keys, quotas, idempotência, Conversation Core, outbox/workers, webhooks, ledger de uso, tracing, healthchecks e isolamento público entre portal cliente e Operations Console. A separação em produção está correta: `evo-api.mago-bot.com` é a central operacional e `app.mago-bot.com/admin` é o portal cliente.

Mas a verdade sem maquiagem é esta: **ainda não somos um produto SaaS de WhatsApp self-service equivalente a Twilio/360dialog/Infobip**. Hoje somos um **alpha avançado, apto para piloto controlado e integração assistida**, não para vender onboarding em escala como se o cliente pudesse conectar qualquer WABA sozinho e sair disparando mensagem no mesmo minuto.

A trava principal não é a tela. É o ciclo oficial de credenciamento e provisionamento da Meta: Embedded Signup, troca server-to-server do código por business token scoped ao cliente, registro do número, assinatura automática da WABA em webhooks, App Review/advanced access e billing. A Meta documenta exatamente esse fluxo e informa que Embedded Signup v2 será depreciado em **15 de outubro de 2026**, exigindo migração para v4.[2]

## Maturidade atual

| Dimensão | Estado atual | Leitura comercial |
|---|---|---|
| Control plane e API própria | Forte | Já há base para pilotos e clientes técnicos |
| Multi-tenancy e isolamento | Implementado | Bom fundamento para SaaS |
| Segurança operacional | Acima de protótipo | Sessões revogáveis, RBAC, cifragem, rate limit, tracing e backups |
| Evolution como provider interno | Correto | Deve continuar como compatibilidade, não como API oficial |
| Meta Cloud outbound | Adapter existe, mas usa token global | Ainda não é conexão Meta por cliente |
| Meta Embedded Signup | **Ausente no código** | Bloqueador de onboarding self-service |
| Templates/mídia/interativos | Parcial/primeiro corte | Falta paridade de produto para uso real |
| Billing e cobrança | Estrutura inicial, sem ciclo financeiro completo | Bloqueador para SaaS pago escalável |
| Portal cliente | Bom esqueleto | Precisa wizard de setup, conexão Meta e diagnóstico guiado |
| Operação autenticada de owner | Não validada de ponta a ponta em produção | Gate obrigatório antes de declarar GA |

## O que a pesquisa de mercado ensina

A Twilio não vende apenas um endpoint de envio. Ela empacota onboarding, senders, templates, webhook principal e fallback, Messaging Services, Conversations, Flex, Studio e observabilidade. A própria documentação exige opt-in explícito, explica a janela de atendimento de 24 horas e separa claramente número, sender, WABA e template.[1] A lição para o Mago Bot é transformar as regras do provider em produto visível: checklist, validação preventiva, status e fallback, em vez de deixar o cliente descobrir tudo no erro 400.

A 360dialog reduz a fricção com Embedded Signup dentro do Hub, trata explicitamente os estados do número — novo, WhatsApp pessoal, WhatsApp Business App ou outra API — e mostra pagamento, OTP, verificação de admin e confirmação de ativos no próprio fluxo.[5] A lição é criar um onboarding que pergunte primeiro **qual é o estado do número**; sem isso o usuário entra num labirinto de migração, coexistência e registro.

A Infobip mostra o caminho de Tech Provider: Business Portfolio, Meta App, Business Verification, App Review, partner solution e registro do sender antes de permitir que a plataforma onboarde clientes.[6] A lição é separar o “Mago Bot funcionando internamente” do “Mago Bot autorizado a onboardear terceiros em escala”. São gates diferentes.

O respond.io trata API, webhooks, paginação, limites por método/path, headers de rate limit, SDK, assinatura de webhook e organização/workspace como produto de integração, não como detalhe escondido.[7] A lição é oferecer SDKs, exemplos, `Retry-After`, paginação previsível, eventos assinados e uma experiência de desenvolvedor minimamente copiável.

A WATI tem papéis específicos para Administrator, Campaign Manager, Template Manager, Operator, Developer, Contact Manager, Dashboard Viewer, Automation Manager e Billing Manager.[8] A lição é evoluir do RBAC de alto nível para permissões por módulo: atendimento, templates, automação, billing, integrações e auditoria.

| Referência | Padrão observado | Adaptação recomendada no Mago Bot |
|---|---|---|
| Twilio | Products + senders + templates + fallback + insights | Catálogo de recursos, capabilities, fallback webhook, template health e usage insights |
| 360dialog | Embedded Signup e tratamento do estado do número | Wizard Meta com novo/migrar/coexistência e checklists de pré-requisitos |
| Infobip | Tech Provider e entidades isoladas | ProviderConnection por tenant/projeto, ambientes e governança de parceiros |
| respond.io | Developer API com rate headers, webhooks assinados, SDK e paginação | Developer portal, SDKs, OpenAPI executável, `Retry-After`, eventos e assinatura padrão |
| WATI | Inbox, automações e RBAC modular | Papéis de agente, templates, automação, billing e painel de atendimento |
| Gupshup | Wallet, Bot Studio, saúde da WABA e portal de parceiros | Créditos/uso, flow builder, conta saudável e canal de parceiros |

## Auditoria exata da Meta no projeto

### Local correto hoje para configurar o WhatsApp do owner

Existe uma tela segura na **Operations Console**, em:

`https://evo-api.mago-bot.com/` → login operacional → aba **WhatsApp / Meta Cloud**.

O formulário atual contém:

| Campo | Uso |
|---|---|
| `Phone Number ID` | Identificador obrigatório do número empresarial na Graph API |
| `WABA ID` | Identificador da WhatsApp Business Account |
| `System User Token` / `access_token` | Credencial server-side para consultar o número e enviar mensagens |
| `App Secret` | Segredo usado na assinatura HMAC dos webhooks |
| `Webhook Verify Token` | Segredo do challenge de verificação do webhook |
| Template de boas-vindas | Nome do template aprovado na Meta |
| Idioma | Por exemplo, `pt_BR` |

O backend grava token, App Secret e verify token cifrados com Fernet na tabela `owner_whatsapp_integrations`. A resposta para o navegador retorna apenas flags como “configurado”; os valores secretos não voltam para a interface. Campos secretos vazios preservam o valor cifrado existente. O botão **Testar conexão** usa o token no servidor para consultar o perfil do número e atualizar telefone, nome verificado e qualidade.

Portanto, respondendo sem enrolação: **o lugar do owner existe e o desenho de armazenamento é correto para uma configuração assistida**. Não cole credenciais em chat, Git, JavaScript, `.env` versionado ou na tela de criação de resource do tenant.

### O que não está correto ainda para um produto multi-tenant

O formulário atual é uma integração especial do **owner**, não o onboarding Meta completo de cada cliente. A criação de `ProviderResource` aceita provider e `provider_resource_id`, mas não aceita nem armazena credencial por cliente. O `MetaCloudAdapter` utilizado pelo envio outbound lê um único `META_SYSTEM_USER_TOKEN` global do ambiente do processo. Isso significa que, hoje, vários tenants não conseguem operar cada um com seu próprio business token scoped, WABA e ciclo de vida independente.

Também existe uma inconsistência importante que precisa ser corrigida antes de chamar a integração de produção completa: a tela do owner salva `app_secret` e `webhook_verify_token` na tabela cifrada, mas o endpoint `/v1/webhooks/meta` atualmente valida `META_APP_SECRET` e `META_WEBHOOK_VERIFY_TOKEN` vindos do ambiente global. Na prática, preencher a tela não substitui a configuração global do webhook. Se esses valores não estiverem no ambiente seguro, o challenge/signature endpoint não ficará operacional mesmo que a integração do owner apareça salva.

### Estado observado na produção

A auditoria foi feita sem imprimir valores. No container produtivo, as variáveis `META_SYSTEM_USER_TOKEN`, `META_APP_SECRET` e `META_WEBHOOK_VERIFY_TOKEN` estão vazias; `META_GRAPH_BASE_URL` e `META_GRAPH_API_VERSION` também não estão explicitamente presentes, embora o código tenha defaults seguros para a URL Graph e a versão. A tabela `owner_whatsapp_integrations` está com **zero registros**.

Conclusão prática: **a tela está pronta para receber a configuração assistida, mas a Meta ainda não está conectada em produção**. Não há atualmente token de owner configurado nem integração ativa que possa ser testada.

## Fluxo que deve existir para virar produto de verdade

O fluxo alvo, inspirado na Meta, Twilio e BSPs, é:

```text
Portal cliente
  → Conectar WhatsApp oficial
  → Embedded Signup Meta v4
  → callback server-side com WABA ID + Phone Number ID + código efêmero
  → troca server-to-server por business token scoped ao cliente
  → registrar telefone na Cloud API
  → assinar webhooks da WABA
  → criar ProviderConnection/ProviderResource ativo
  → wizard de teste: template aprovado + mensagem de teste
  → API key + scopes + documentação + observabilidade
  → mensagem outbound idempotente
  → webhook de status
  → ledger de uso + billing/reconciliação
```

A Meta afirma que o Embedded Signup retorna WABA ID, business phone number ID e código trocável, e que o servidor deve executar a troca do código, registrar o número e assinar os webhooks da WABA.[2] O Mago Bot ainda precisa implementar esse caminho em vez de depender de colagem manual de token.

## O que falta, por prioridade

### P0 — Bloqueadores de produto oficial

**Embedded Signup v4 e Tech Provider.** Criar o fluxo oficial dentro do portal cliente, preparar Meta App, permissões, App Review/advanced access, Business Verification e migração para v4 antes da data de depreciação documentada pela Meta.[2] Sem isso, o cliente depende de suporte manual e o produto não escala.

**ProviderConnection por tenant.** Criar uma entidade própria para WABA, phone number, business token cifrado, status, versão, ambiente, data de expiração/rotação, último healthcheck, erro normalizado e vínculo com projeto/tenant. O token do cliente não pode ficar em `META_SYSTEM_USER_TOKEN` global.

**Provisionamento automático pós-Embedded Signup.** Depois do callback, executar troca do código, registro do telefone, subscribe da WABA, validação de permissões e primeiro healthcheck. Cada etapa precisa ser idempotente, auditável e reexecutável sem duplicar ativos.

**Webhook multi-tenant consistente.** Resolver o tenant pelo WABA/Phone Number ID, validar assinatura com a política correta do app Meta, deduplicar, registrar status, atualizar conversa e expor métricas. A configuração visual e a configuração efetivamente usada pelo endpoint precisam ser a mesma fonte de verdade.

### P1 — Produto vendável para clientes reais

**Templates Meta.** Criar, listar, sincronizar status, exibir categoria/idioma/qualidade, orientar aprovação e bloquear uso fora da janela de atendimento quando template for obrigatório. A Twilio coloca gestão de templates no Console; esse é o padrão de UX a seguir.[1]

**Mensagens além de texto.** Completar mídia, documentos, áudio, localização, botões, listas, replies, templates e interativos com capabilities explícitas por provider. A API própria deve normalizar o contrato e devolver erro previsível quando a capability não existe.

**Billing real.** Transformar `Subscription` e ledger em cobrança operacional: checkout, assinatura, fatura, créditos ou plano, repasse/markup Meta, limites, grace period, webhooks de pagamento, reconciliação, falha de cobrança e portal de faturamento. Sem isso há API, mas não há negócio repetível.

**Onboarding e suporte.** Wizard com pré-requisitos, estado do número, checklist de verificação, teste de webhook, teste de template, diagnóstico por etapa e abertura de suporte. O cliente não pode precisar de um engenheiro para descobrir por que o número está em review.

**Developer experience.** Publicar OpenAPI real, SDKs iniciais, exemplos curl/Python/Node, Postman collection, paginação, idempotência, `Retry-After`, códigos de erro estáveis, changelog e status page. O padrão de API do respond.io mostra a importância de rate headers e paginação previsível.[7]

### P2 — Diferenciação contra players de painel

**Inbox e equipe.** O Conversation Core já é uma base boa, mas a UI precisa permitir atribuição, filas, SLA, notas internas, handoff, respostas, encerramento e permissões por papel. A matriz de papéis da WATI é uma referência prática para não deixar “admin” com acesso universal.[8]

**Automação visual.** Um flow builder inicial, inspirado em Studio/Bot Studio, pode começar com gatilhos, condições, espera, chamada HTTP, template e handoff humano. Não precisa nascer com mil blocos; precisa ser determinístico, auditável e fácil de depurar.

**Analytics de negócio.** Medir entrega, leitura, resposta, conversão, tempo até primeira resposta, custo por conversa, qualidade do número, falha por template e ROI de campanha. A operação precisa enxergar saúde da WABA e do funil, não só “HTTP 200”.

**Parceiros e white-label.** Depois do core, criar subcontas/organizations, delegação de agência, limites por parceiro, suporte e faturamento por subconta. A rota de Tech Provider e plataformas BSP mostra que esse é o caminho para distribuição, não apenas venda direta.[6]

## Critério objetivo para declarar “produto”

O Mago Bot deve ser considerado **produto piloto** quando conseguir conectar um WABA de teste, enviar template aprovado, receber webhook de mensagem/status, registrar tudo no tenant correto, emitir API key, aplicar quota, sobreviver a retry/duplicata e permitir rollback sem intervenção manual no banco.

Deve ser considerado **produto comercial GA** quando, além disso, um cliente novo conseguir concluir Embedded Signup v4 sem suporte técnico, configurar billing, receber documentação/SDK, operar seus papéis, ver consumo/fatura, administrar templates, tratar erro de provider e desligar/rotacionar a conexão com trilha de auditoria.

Hoje estamos entre esses dois pontos: **piloto técnico avançado, ainda não GA self-service**.

## Próxima sequência recomendada

1. Configurar um WABA/Phone Number de teste do owner em ambiente controlado, sem enviar mensagens reais para terceiros.
2. Corrigir a fonte de verdade dos segredos do webhook e separar explicitamente `OwnerWhatsAppIntegration` de `ProviderConnection` por tenant.
3. Implementar Embedded Signup v4, callback idempotente e provisionamento server-to-server.
4. Completar templates, status, mídia e teste de jornada.
5. Fechar billing, reconciliação e portal de consumo.
6. Executar E2E autenticado, carga, retry, duplicata, restore e teste de desligamento/rotação.
7. Só então abrir onboarding comercial em escala.

## Referências

[1]: https://www.twilio.com/docs/whatsapp/api "Twilio — Overview of the WhatsApp Business Platform with Twilio"
[2]: https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview "Meta — Embedded Signup"
[3]: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started "Meta — WhatsApp Cloud API Get Started"
[4]: https://whatsappbusiness.com/developers/developer-hub/ "WhatsApp Business — Developer Hub"
[5]: https://docs.360dialog.com/docs/hub/embedded-signup "360dialog — Embedded Signup"
[6]: https://www.infobip.com/docs/whatsapp/tech-provider-program "Infobip — Tech Provider Program"
[7]: https://developers.respond.io/ "respond.io — API Documentation"
[8]: https://support.wati.io/en/articles/11463020-understanding-different-roles-and-permissions-in-wati "WATI — Roles and Permissions"
[9]: https://docs.gupshup.io/docs/onboarding-guide "Gupshup — Onboarding Guide"
