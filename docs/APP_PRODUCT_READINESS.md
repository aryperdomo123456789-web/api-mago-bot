# API Mago Bot — prontidão do produto em `app.mago-bot.com`

## Diagnóstico executivo

A API Mago Bot já possui uma fundação de control plane consistente e um backend customer-scoped com tenants, projetos, providers, canais Evolution, onboarding, inbox, webhooks, API keys e integrações cifradas. O gargalo atual não é ausência completa de infraestrutura; é a distância entre esses contratos de backend e a experiência que o cliente encontra no portal.

O caminho oficial do produto é `app.mago-bot.com`, com login em `/admin`. Depois da autenticação, o portal carrega visão geral, seleção de tenant, projetos e as seções **Primeiro valor**, **Canais** e **Inbox** customer-scoped, além de conversas e consentimento opcional para boas-vindas. As áreas de API keys, webhooks e uso ainda exigem fechamento de UI e E2E antes de serem anunciadas como completas.

> Conclusão: o produto está pronto para pilotos técnicos controlados, mas ainda não oferece uma jornada self-service completa. O próximo ganho de produto vem de conectar a interface cliente aos endpoints que já existem, não de criar mais endpoints isolados.

## Mapa do caminho atual

| Etapa | Estado atual | Impacto para o cliente |
|---|---|---|
| Apresentação → `app.mago-bot.com` | Abre o portal e redireciona para `/admin` | Correto, mas a CTA precisa deixar claro que é o portal de operação |
| Login, cadastro e reset | Implementados | Permite entrada de equipe e criação de ambiente |
| Tenant selecionado | Carregado por sessão/membership | Base correta para isolamento |
| Projeto e provider | Criação de projeto disponível | Primeiro ambiente pode ser criado, mas o fluxo ainda é pouco guiado |
| Onboarding | Backend e seção **Primeiro valor** disponíveis | Checklist customer-scoped promovido |
| Canal Evolution | Lifecycle/QR/status e seção **Canais** disponíveis | E2E real com número controlado ainda pendente |
| Meta Cloud oficial | Adapters e integração server-side disponíveis | Falta fluxo customer-scoped equivalente no portal |
| Inbox | Backend com filas, assignment e estados disponível | Seção **Inbox** promovida; E2E real ainda pendente |
| API keys | Backend de emissão/revogação disponível | UI ainda é placeholder |
| Webhooks | Backend de criação, rotação e disable disponível | UI ainda é placeholder |
| Uso e quotas | Backend/observabilidade existentes | UI ainda é placeholder |
| Boas-vindas | Opt-in no cadastro e worker owner preparado | Falta E2E real com canal conectado |

## Contrato de providers

O portal deve exibir duas escolhas semanticamente separadas. **Meta Cloud** é o provider oficial, baseado na WhatsApp Business Platform e em credenciais server-side. **Evolution** é uma camada de compatibilidade premium para pilotos e operações opt-in; ela não deve ser apresentada como API oficial da Meta. O cliente deve sempre saber qual provider está ativo antes de criar um canal ou enviar uma mensagem.

## Ordem de implementação para primeiro valor

A primeira tela pós-login deve orientar o cliente em uma sequência mensurável: selecionar ou criar a organização, criar o projeto, escolher explicitamente o provider, conectar o canal, verificar o estado de saúde, criar a primeira fila e executar uma simulação segura. Depois disso, o cliente deve chegar ao inbox e enxergar a conversa, a timeline e os estados de atendimento.

A UI deve consumir os contratos existentes de onboarding, canais customer-scoped e inbox. Não deve aceitar secrets em texto livre fora dos formulários próprios, não deve mostrar tokens depois da emissão e deve exigir `Idempotency-Key` nas mutations de envio. Os estados de loading, vazio, erro recuperável e sucesso precisam ser visíveis para que o usuário não interprete uma tela vazia como produto quebrado.

## Gaps que impedem venda self-service

O portal já possui wizard de Primeiro valor, seção de Canais com provider explícito e lifecycle Evolution, e Inbox com filas/assignment. Ainda precisa fechar a emissão e rotação customer-scoped de API keys, UI de webhooks, uso/quotas, composer completo e testes E2E com um número controlado.

A camada comercial precisa completar planos, checkout/faturamento e limites de uso antes de escalar aquisição. A camada técnica precisa executar o E2E com um número de laboratório, incluindo conexão, webhook inbound, conversa, claim, resposta idempotente e estado de entrega. Nenhuma dessas validações deve ser declarada como concluída antes de ocorrer com um destinatário controlado e opt-in.

## Definição de pronto para o primeiro piloto

| Gate | Critério de aceite |
|---|---|
| Acesso | Cliente cria conta, confirma e-mail quando configurado e entra no próprio tenant |
| Isolamento | Tentativas cross-tenant retornam 403/404 sem vazamento |
| Onboarding | Checklist orienta do projeto ao primeiro teste simulado |
| Canal | Cliente escolhe Meta Cloud ou Evolution e vê status/saúde sem segredo bruto |
| Inbox | Conversa aparece em fila, pode ser reivindicada, atribuída, pausada e resolvida |
| Mensagem | Um envio controlado aceita idempotência e possui estado observável |
| Webhook | Evento duplicado é deduplicado e a assinatura/secret não é reexibida |
| Observabilidade | Request ID, auditoria, logs sanitizados e healthchecks estão disponíveis |
| Comercial | Plano, quota, upgrade e política de provider são compreensíveis antes da compra |

## Próximo movimento

Validar em canário e executar o piloto opt-in com o número de laboratório. Em paralelo, concluir API keys, webhooks, uso/quotas e billing para liberar a jornada self-service comercial. O owner só deve ser usado para provisionamento administrativo; o cliente final deve percorrer a jornada customer-scoped pelo próprio portal.

Status deste documento: auditoria de código e navegação pública concluída em 27 de agosto de 2026. O E2E com número real ainda é um gate pendente.
