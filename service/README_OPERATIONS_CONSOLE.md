# API Mago Bot — Operations Console

> Este manual descreve somente a área owner do **produto API Mago Bot**. O Mago Bot CRM é outro produto, no repositório `project-hello`, com owner em `mago-bot.com/owner/login` e usuário em `mago-bot.com`.

## Estado da entrega

A Operations Console é a superfície administrativa do **API Mago Bot** e deve ser publicada em `https://evo-api.mago-bot.com/ops`. O portal de usuário permanece em `https://app.mago-bot.com/admin`; a documentação fica em `https://app.mago-bot.com/docs`. A implementação atual foi validada em canário isolado e não deve ser promovida para produção sem um gate explícito, backup recente e rollback confirmado.

## Superfícies

| Superfície | Domínio | Função | Política |
|---|---|---|---|
| Operations Console | `evo-api.mago-bot.com/ops` | Administração, operações, filas, tenants e auditoria | `owner`, `platform_superadmin`, `platform_operator`, `platform_support` |
| Portal usuário | `app.mago-bot.com/admin` | Projetos, conversas, chaves, webhooks e consumo do tenant | Papéis `tenant_*` e `customer_common` |
| Evolution provider | Rotas provider do `evo-api` | Adapter de compatibilidade para WhatsApp | Nunca é apresentado como a API própria |
| Manager Evolution | `/manager` | Interface interna da Evolution | Bloqueada publicamente |

A autorização usa o hostname efetivo do request no backend. Nenhum campo enviado pelo browser escolhe a superfície. Rotas administrativas no domínio cliente e rotas tenant no domínio operacional retornam `404`; isso evita descoberta desnecessária e reduz o risco de bypass. O login incompatível com a superfície não cria sessão.

## Abas administrativas

A central possui quinze abas: Overview, Proprietário, Usuários, Clientes/Tenants, Projetos, Licenças e API Keys, Planos e Trials, Parceiros, WhatsApp/Meta Cloud, Evolution API, Estatísticas, Uso e quotas, Filas e falhas, Alertas e Auditoria. Ela é o cockpit de governança da **API Mago Bot**, não o painel de atendimento do CRM.

As mutações usam endpoints modernos sob `/v1/ops` e registram `AuditEvent` append-only com ator, request ID, IP, user-agent, recurso, resultado e metadados sanitizados. Tokens de licença são entregues uma única vez; hashes e segredos não são serializados para o navegador.

## Endpoints administrativos principais

| Família | Endpoints |
|---|---|
| Conta | `GET/PUT /v1/ops/owner/profile` |
| Usuários | `GET/POST /v1/ops/users`, `PATCH/DELETE /v1/ops/users/{user_id}` |
| Projetos | `GET/POST /v1/ops/license-projects`, `PATCH /v1/ops/license-projects/{project_id}` |
| Licenças | `GET/POST /v1/ops/licenses`, `POST /v1/ops/licenses/validate`, `POST /v1/ops/licenses/{license_id}/revoke` |
| Planos | `GET /v1/ops/plans`, `PATCH /v1/ops/plans/{slug}` |
| Clientes | `GET /v1/ops/customers`, `PATCH /v1/ops/customers/{customer_id}` |
| Parceiros | `GET /v1/ops/partners`, `PATCH /v1/ops/partners/{partner_id}` |
| Operação | `GET /v1/ops/stats`, `GET /v1/ops/usage`, `GET /v1/ops/providers/evolution` |

As rotas legadas continuam compatíveis somente na superfície operacional. O portal cliente usa exclusivamente o control plane multi-tenant e não recebe as rotas globais legadas de conta, usuários, projetos, licenças, planos, trials, keys ou parceiros.

## Segurança e operação

O login utiliza sessão server-side revogável e cookie host-only. O papel `platform_partner` não acessa a central administrativa. A central não retorna segredos de provider. Mutação de usuário owner é protegida; alteração de papel exige owner ou superadmin. A tela escapa dados vindos do banco antes de renderizar e não utiliza API key no browser.

O canário possui app, PostgreSQL, Redis e workers próprios. A validação executada com `Host` explícito cobriu portal, central, OpenAPI, health, rotas legadas, bloqueio cruzado e estado `healthy` dos workers. A mesma imagem não deve ser promovida sem novo backup e sem validação dos dois domínios.

## Critério de promoção

A promoção exige: backup recente catalogado; `nginx -t`; verificação de migrations; healthchecks Docker verdes; login owner confirmado; teste de cada família de endpoint sem segredo real; `app/admin` funcionando; `evo-api/ops` funcionando; Manager bloqueado; Evolution provider preservado; validação de logs sem erro novo; e rollback por troca de imagem/configuração já preparado.

A prova canária atual passou. A promoção pública desta migração permanece deliberadamente pendente até aprovação explícita do proprietário, conforme o prompt operacional.
