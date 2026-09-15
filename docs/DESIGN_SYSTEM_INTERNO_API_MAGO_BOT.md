# Design system interno — API Mago Bot

**Escopo:** interfaces autenticadas de `app.mago-bot.com` e `evo-api.mago-bot.com`.
**Fora do escopo:** CRM `mago-bot.com` e sua aplicação pública.

## Direção visual

O produto interno usa a linguagem espacial do `host.mago-bot.com`: fundo profundo, malha técnica discreta, halos ciano/violeta, superfícies translúcidas e hierarquia tipográfica forte. O efeito 3D é usado como profundidade e orientação, não como decoração que prejudica leitura ou operação.

## Experiências

| Superfície | Usuário | Navegação principal |
|---|---|---|
| Operations Console | owner, superadmin, operator e suporte autorizado | Overview, clientes, projetos, providers, Evolution, e-mail, filas, alertas e auditoria |
| Portal customer-scoped | usuário comum e owner em contexto de tenant | Visão geral, primeiro valor, projetos/providers, canais, inbox, conversas, API keys, webhooks e uso |

## Regras de UX

- A aba ativa sempre possui contraste, marcador lateral e título correspondente no topo.
- Toda mutação exibe estado de processamento, bloqueia clique duplicado e retorna sucesso ou erro recuperável.
- Estados vazios explicam o próximo passo; não aparecem como uma tela sem contexto.
- Estados de canal diferenciam `connected`, `connecting`, `qr_pending`, `disconnected`, `degraded` e `failed`.
- QR, tokens, API keys e segredos nunca ficam no HTML, no log ou em respostas posteriores.
- O layout funciona em desktop e mobile; em telas menores a navegação vira drawer acessível.
- O movimento é reduzido automaticamente quando `prefers-reduced-motion` está ativo.
- O visual não altera contratos de API, RBAC, tenant isolation, provider ou persistência.

## Implementação

- `service/app/assets/ops.css`: design system da Operations Console.
- `service/app/assets/platform.css`: design system do Portal customer-scoped.
- `service/app/routes/ops_ui.py` e `platform_ui.py`: cache-bust dos bundles internos.
- `ops-app.js` e `platform-app.js`: comportamento de navegação e ações; preservados nesta promoção.

## Critério de aceite

Considera-se a camada visual promovida quando as duas áreas carregam sem erro, a navegação lateral permanece utilizável, os estados de loading/erro/vazio continuam visíveis, o mobile abre/fecha o menu e os fluxos de canal continuam acionando os mesmos endpoints.

Esta camada é uma evolução visual e de usabilidade. Ela não representa, sozinha, a conclusão do E2E real de WhatsApp, billing, API keys, webhooks ou inbox.
