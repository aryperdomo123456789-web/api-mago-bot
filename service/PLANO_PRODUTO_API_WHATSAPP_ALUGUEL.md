# Plano especializado: plataforma de API WhatsApp por aluguel

Data: 26/08/2026  
Objetivo: transformar a base atual de licenciamento, Mago Bot e Evolution API em uma plataforma profissional de acesso alugado para automação WhatsApp, com uma segunda linha futura baseada na WhatsApp Business Platform oficial.

## 1. Decisão estratégica

A ideia é viável, mas o produto precisa ter dois modos explicitamente separados:

### Linha A — API WhatsApp conectada por Evolution

Usa a Evolution API já instalada no servidor para gerenciar conexões via WhatsApp Web/Baileys, QR code, pairing code, mensagens e webhooks.

Posicionamento correto:

> API de automação WhatsApp compatível com os principais fluxos de mensageria, hospedada e gerenciada pela nossa plataforma.

Não deve ser anunciada como “API oficial do WhatsApp”. A Evolution é uma camada de integração diferente da WhatsApp Business Platform oficial, com riscos técnicos, operacionais e de política próprios.

### Linha B — API oficial

Futuro módulo integrado à WhatsApp Business Platform através de Meta Cloud API ou parceiro oficial/BSP/Tech Provider.

Posicionamento correto:

> WhatsApp Business Platform oficial, com onboarding de WABA, números comerciais, templates, webhooks, limites e cobrança conforme as regras da Meta e do provedor.

As duas linhas podem compartilhar painel, clientes, cobrança, métricas e chaves da nossa plataforma, mas não devem compartilhar o mesmo modelo técnico de conexão.

## 2. Referências de mercado para espelhamento

### 2.1 Twilio — referência de experiência de plataforma

O modelo da Twilio é uma boa referência para:

- onboarding guiado;
- catálogo de senders/números;
- credenciais por conta;
- webhooks de entrada;
- callbacks de status de saída;
- fallback de webhook;
- console operacional;
- documentação por linguagem;
- controle de opt-in, templates e janela de atendimento.

A documentação da Twilio descreve a necessidade de número WhatsApp, configuração de webhook, status de mensagens e janela de atendimento de 24 horas. [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp/api)

### 2.2 360dialog — referência de parceiro e revenda

O 360dialog é a melhor referência para o futuro módulo oficial multi-cliente, porque trabalha com:

- Partner Hub;
- onboarding integrado;
- gestão de clientes e números;
- Partner API;
- API keys por número;
- eventos de WABA;
- limites de mensagens;
- qualidade de número e templates;
- Tech Provider Program.

A documentação do Partner API mostra a ideia de administrar WABAs e números de clientes programaticamente. [360dialog Partner API](https://docs.360dialog.com/partner/partner-api/intro)

O fluxo de Tech Provider exige empresa verificada, aplicativo Meta, aprovação da solução e processo de onboarding. [360dialog Tech Provider](https://docs.360dialog.com/partner/get-started/tech-provider-program/becoming-a-meta-tech-provider-a-step-by-step-guide)

### 2.3 Padrões que devemos copiar

Não devemos copiar código proprietário. Devemos copiar padrões de produto:

| Capacidade | Referência | Aplicação no nosso produto |
|---|---|---|
| Portal de clientes | Twilio Console | Painel multi-tenant |
| Onboarding de números | Twilio/360dialog | Wizard de conexão e ativação |
| Partner API | 360dialog | Futura administração da API oficial |
| Webhooks e status | Twilio/360dialog | Eventos uniformes para clientes |
| Limites e qualidade | 360dialog/Meta | Quotas, alertas e bloqueios preventivos |
| Documentação | Twilio | Docs pública, SDKs e exemplos |
| Billing | Twilio/360dialog | Aluguel, consumo, excedentes e suspensão |
| Suporte operacional | ambos | Status page, auditoria e runbooks |

## 2.4 Catálogo completo de módulos desejados

Além da API de WhatsApp, o produto pode evoluir para uma plataforma de comunicação, conversas, autenticação e dados de clientes. A imagem de referência apresenta o catálogo da Twilio; vamos usar esse catálogo como mapa de produto, sem assumir que todos os módulos serão construídos de uma vez.

### Conversas

#### Memória de Conversa

Objetivo: manter contexto persistente do cliente entre mensagens, canais, atendentes e agentes de IA.

Construção planejada:

- perfil de contexto por cliente;
- resumo automático de conversas;
- fatos importantes com origem e data;
- preferências e consentimentos;
- memória curta, longa e episódica;
- controles de retenção e exclusão;
- busca contextual por tenant;
- permissão para o cliente exportar ou apagar a memória.

Dependências: banco de conversas, armazenamento de embeddings, política LGPD, criptografia e controle de acesso.

#### Orquestrador de Conversas

Objetivo: coordenar a mesma conversa entre WhatsApp, SMS, voz, e-mail, chat web, IA e atendente humano.

Construção planejada:

- máquina de estados de conversa;
- roteamento por intenção;
- handoff para humano;
- regras por canal;
- prioridade e SLA;
- fallback de canal;
- histórico unificado;
- idempotência de eventos;
- retomada após falhas.

Dependências: módulo de mensagens, voz, e-mail, fila, CRM e Flex/central de atendimento.

#### Inteligência de Conversação

Objetivo: extrair intenção, sentimento, tópicos, resumo, risco de churn, qualidade do atendimento e oportunidades.

Construção planejada:

- transcrição de áudio;
- resumo automático;
- classificação por intenção;
- análise de sentimento;
- detecção de urgência;
- avaliação de atendimento;
- operadores de IA configuráveis;
- revisão humana de resultados;
- trilha de modelo, prompt e versão.

Dependências: provedor de IA, política de dados sensíveis, observabilidade de custo e consentimento.

#### Retransmissão de Conversa / Conversation Relay

Objetivo: criar agentes de voz em tempo real com STT, TTS, WebSocket e transferência para atendente.

Construção planejada:

- streaming de áudio;
- speech-to-text;
- text-to-speech;
- escolha de LLM;
- interrupção natural do agente;
- transferência para humano;
- gravação e transcrição opcional;
- controle de latência;
- limite de duração e custo.

Dependências: telefonia/SIP, provedor de voz, WebSocket de baixa latência e política de gravação.

### Comunicações

#### Mensagens

Camada unificada para:

- WhatsApp Evolution;
- WhatsApp oficial;
- SMS;
- RCS;
- templates;
- mídia;
- status de entrega;
- filas;
- retry;
- opt-in e opt-out;
- idempotency key;
- rastreamento de custo.

O recurso deve ter um contrato nosso, com adaptadores para cada canal. O cliente não deve depender do formato interno da Evolution.

#### Voz

Inclui:

- chamadas de entrada e saída;
- SIP trunk;
- gravação opcional;
- URA;
- filas de atendimento;
- transferência;
- status de chamada;
- cobrança por minuto;
- proteção contra abuso e chamadas automatizadas indevidas.

Essa parte não é fornecida pela Evolution API e exigirá provedor de telefonia separado.

#### E-mail

Inclui:

- envio transacional;
- SMTP;
- domínio e DKIM;
- SPF e DMARC;
- templates;
- eventos de entrega, abertura e bounce;
- supressão de destinatários;
- reputação do domínio;
- limites por tenant.

Exige integração com provedor SMTP/Email API e não deve compartilhar o mesmo serviço de entrega do WhatsApp.

#### Números de telefone

Catálogo para:

- números locais;
- números gratuitos;
- 10DLC;
- códigos curtos;
- números habilitados para WhatsApp;
- portabilidade e verificação;
- aluguel, renovação e devolução;
- país, região e capacidade;
- documentação regulatória.

Cada número deve ser tratado como recurso com proprietário, estado, provedor, custo, país e regras de uso.

#### API de vídeo

Inclui:

- salas;
- participantes;
- tokens temporários;
- gravação opcional;
- transmissão de áudio/vídeo;
- limites por plano;
- auditoria de participantes;
- cobrança por minuto e armazenamento.

Exige provedor de vídeo/WebRTC e infraestrutura própria de mídia. Não é um recurso da Evolution.

#### Flex / Central de Atendimento

Objetivo: criar uma central omnichannel para agentes humanos.

Inclui:

- filas;
- agentes;
- habilidades;
- distribuição de tarefas;
- histórico do cliente;
- WhatsApp, SMS, voz, e-mail e chat;
- supervisão;
- gravação;
- indicadores de SLA;
- plugins de painel;
- handoff entre IA e humano.

O Flex deve ser tratado como referência de experiência. A primeira versão pode ser construída como um módulo interno menor, usando filas, agentes e tarefas antes de tentar reproduzir uma plataforma completa.

### Autenticação e identidade

#### Verificar / Verify

Módulo para:

- OTP por SMS;
- OTP por WhatsApp oficial;
- OTP por voz;
- OTP por e-mail;
- TOTP;
- passkeys;
- push;
- limite de tentativas;
- antifraude;
- verificação de telefone e e-mail.

O produto não deve enviar OTP pela Evolution sem uma avaliação específica de risco e política. Para autenticação comercial, priorizar provedor oficial e canais com controle antifraude.

#### Pesquisa / Lookup

Módulo para validar e enriquecer números:

- formato E.164;
- país;
- operadora quando disponível;
- tipo de linha;
- possibilidade de WhatsApp quando permitido pelo provedor;
- normalização;
- detecção de duplicidade;
- bloqueio de números inválidos.

O resultado deve ser armazenado com finalidade, prazo de retenção e controle de custo. Não usar Lookup para construir bases de spam.

### Dados do cliente

#### Conexões

Ingestão de dados de:

- API própria;
- webhooks;
- bancos;
- CRM;
- e-commerce;
- formulários;
- WhatsApp;
- mensagens;
- pagamentos.

Cada conexão deve possuir credenciais, escopo, status, último evento, erro e política de sincronização.

#### Armazéns

Integração com:

- PostgreSQL;
- MySQL;
- data warehouse;
- data lake;
- S3/MinIO;
- exportação de eventos;
- pipelines de uso e faturamento.

O armazém não deve receber segredos ou dados fora do tenant autorizado.

#### Protocolos

Camada para governança de dados:

- schemas de eventos;
- contratos de payload;
- versionamento;
- consentimento;
- origem do dado;
- qualidade;
- retenção;
- classificação de PII;
- trilha de transformação.

#### Unificar / Unify

Criação de perfil unificado do cliente:

- telefone;
- e-mail;
- identificadores externos;
- histórico de compras;
- conversas;
- consentimentos;
- eventos;
- resolução de identidade;
- conflitos de dados;
- visão 360º.

#### Envolver / Engage

Ativação de públicos e jornadas:

- segmentos;
- campanhas;
- eventos de entrada e saída;
- regras de frequência;
- supressão;
- personalização;
- atribuição;
- consentimento;
- limites de envio.

#### Públicos / Audiences

Ferramenta para criar públicos com base em:

- comportamento;
- plano;
- status do aluguel;
- última interação;
- valor gasto;
- região;
- consentimento;
- intenção;
- risco de churn.

Todo público precisa ter origem, query, data de atualização, finalidade e limite de uso.

#### Viagens / Journeys

Orquestração visual de jornadas:

- gatilho;
- espera;
- condição;
- mensagem;
- chamada HTTP;
- tarefa humana;
- experimento;
- saída;
- pausa por opt-out;
- janela de atendimento;
- controle de frequência.

As jornadas devem ser versionadas e testáveis antes da publicação.

### Mapa de construção própria versus integração

| Módulo | Pode começar com a base atual? | Estratégia |
|---|---:|---|
| Mensagens WhatsApp Evolution | Sim | Adapter Evolution + fila |
| API oficial WhatsApp | Não somente | Meta Cloud API ou BSP/Tech Provider |
| Memória de conversa | Parcial | Construir sobre logs e banco de conversas |
| Orquestrador | Parcial | Máquina de estados + filas |
| Inteligência | Parcial | Integrar provedor de IA com governança |
| Conversation Relay | Não | Provedor de voz/WebSocket |
| SMS/RCS | Não | Provedor de telecom |
| Voz/SIP | Não | Carrier/SIP provider |
| E-mail/SMTP | Não | Email API/SMTP provider |
| Números | Não somente | Carrier/BSP e compliance por país |
| Vídeo | Não | WebRTC/provedor de vídeo |
| Flex/atendimento | Parcial | Construir módulo inicial ou integrar plataforma |
| Verify | Não somente | Provedor de identidade/OTP |
| Lookup | Não somente | Provedor de dados telefônicos |
| Connections | Parcial | Integrar webhooks e APIs existentes |
| Warehouses | Parcial | ETL/ELT e conectores |
| Protocols | Sim | Schema registry e governança próprios |
| Unify | Parcial | Identity resolution própria |
| Engage | Parcial | Segmentação e ativação próprias |
| Audiences | Sim | Query builder sobre eventos e perfis |
| Journeys | Sim, fase inicial | Workflow engine e filas |

O catálogo oficial da Twilio separa comunicações, dados de clientes e autenticação; essa divisão é adequada para nosso domínio e evita misturar mensageria, billing, dados e identidade no mesmo serviço. [Catálogo de preços e produtos Twilio](https://www.twilio.com/en-us/pricing/customer-data) · [Twilio Verify](https://www.twilio.com/docs/verify) · [Twilio Flex](https://www.twilio.com/docs/flex)

## 3. O que a base atual já entrega

### Central de licenças

Já existe:

- FastAPI;
- emissão de tokens;
- hash de tokens no PostgreSQL;
- expiração;
- revogação;
- projetos;
- scopes;
- auditoria;
- painel administrativo;
- planos e trials;
- cadastro de parceiros;
- documentação OpenAPI básica;
- domínio público de documentação.

Arquivos principais:

- `service/app/routes/licenses.py`;
- `service/app/routes/product.py`;
- `service/app/routes/account.py`;
- `service/app/models.py`;
- `service/app/db.py`.

### Mago Bot

Já existe:

- painel de administração;
- usuários;
- instâncias WhatsApp;
- integração com Evolution;
- QR code/pairing;
- webhooks Evolution;
- envio de texto e mídia;
- cache Redis;
- deduplicação de eventos;
- locks distribuídos;
- logs de mensagens;
- cobrança Ciabra;
- testes e script de carga de webhook.

### Evolution instalada

Foi encontrada uma instalação ativa separada:

- `evoapicloud/evolution-api:v2.3.7`;
- container `evolution_api`;
- porta interna 8080 publicada no host como 4348;
- Redis próprio;
- volumes persistentes de instâncias e store;
- banco MySQL remoto;
- webhook global apontando para o Mago Bot;
- duas instâncias WhatsApp ativas no banco do Mago Bot.

O diagnóstico operacional completo está em [AUDITORIA_TECNICA_OPERACIONAL.md](./AUDITORIA_TECNICA_OPERACIONAL.md).

## 4. Produto que deve ser construído

O produto não deve vender uma “chave de API” isolada. Deve vender um recurso alugado com ciclo de vida completo:

```text
Cliente
  ↓
Plano e pagamento
  ↓
Alocação de recurso
  ↓
Instância Evolution ou número oficial
  ↓
API key do cliente
  ↓
Uso, métricas e limites
  ↓
Renovação, suspensão ou encerramento
```

### Entidades comerciais

- Customer: cliente responsável pela conta.
- Organization: empresa ou workspace do cliente.
- User: usuário do painel.
- Project: aplicação do cliente.
- Subscription: assinatura/plano.
- Rental: aluguel de um recurso.
- Resource: instância Evolution ou número oficial.
- Credential: segredo de acesso à API.
- API key: chave entregue ao cliente.
- Usage record: consumo por período.
- Invoice: cobrança.
- Suspension: bloqueio comercial ou técnico.
- Audit event: evento imutável de segurança e operação.

### Tipos de recurso

```text
evolution_instance
official_phone_number
official_waba
```

O mesmo aluguel deve apontar para um adaptador de provedor, nunca para regras espalhadas pelo painel.

## 5. Arquitetura alvo

```text
                           ┌────────────────────────────┐
                           │ Painel web / Portal cliente │
                           └──────────────┬─────────────┘
                                          │
                           ┌──────────────▼─────────────┐
                           │ API de produto / Gateway    │
                           │ auth, tenant, quota, billing│
                           └─────┬──────────┬─────────────┘
                                 │          │
                    ┌────────────▼───┐  ┌──▼────────────────┐
                    │ Licensing       │  │ Rental/Provisioning│
                    │ keys, scopes    │  │ recursos, lifecycle│
                    └────────────┬───┘  └──┬────────────────┘
                                 │         │
              ┌──────────────────▼─────────▼─────────────────┐
              │ Orquestrador de provedores                    │
              │ EvolutionAdapter | OfficialCloudAdapter       │
              └───────────────┬────────────────┬──────────────┘
                              │                │
                   ┌──────────▼──────┐  ┌────▼───────────────┐
                   │ Evolution API   │  │ WhatsApp oficial   │
                   │ QR, Baileys     │  │ Meta/BSP/Cloud API │
                   └─────────────────┘  └────────────────────┘

  Webhook ingress → fila → workers → banco de eventos → webhooks do cliente
                         │
                         └── métricas, billing e auditoria
```

### Princípios

1. O cliente nunca acessa diretamente a Evolution.
2. O cliente recebe uma API key da nossa plataforma.
3. A API key aponta para um tenant, projeto, aluguel e recurso.
4. O provedor é escondido atrás de um adaptador.
5. Webhook sempre responde rapidamente e processa de forma assíncrona.
6. Billing, licença e provedor têm estados independentes.
7. Uma falha de um cliente não pode derrubar as instâncias dos demais.

## 6. Contrato de API que devemos oferecer

O cliente deve consumir uma API estável nossa, não os endpoints internos da Evolution.

### Administração da conta

```text
POST   /v1/auth/login
GET    /v1/account
GET    /v1/projects
POST   /v1/projects
GET    /v1/usage
GET    /v1/invoices
```

### Aluguéis

```text
GET    /v1/rentals
POST   /v1/rentals
GET    /v1/rentals/{id}
POST   /v1/rentals/{id}/renew
POST   /v1/rentals/{id}/suspend
POST   /v1/rentals/{id}/cancel
```

### Instâncias Evolution

```text
POST   /v1/evolution/instances
GET    /v1/evolution/instances
GET    /v1/evolution/instances/{id}
GET    /v1/evolution/instances/{id}/connect
GET    /v1/evolution/instances/{id}/qr
GET    /v1/evolution/instances/{id}/state
POST   /v1/evolution/instances/{id}/restart
DELETE /v1/evolution/instances/{id}
```

### Mensagens normalizadas

```text
POST /v1/messages
GET  /v1/messages/{id}
GET  /v1/messages
```

Payload de exemplo:

```json
{
  "resource_id": "res_123",
  "to": "+5511999999999",
  "type": "text",
  "text": "Mensagem de teste",
  "idempotency_key": "msg_20260826_0001"
}
```

Resposta:

```json
{
  "id": "msg_abc123",
  "status": "accepted",
  "provider": "evolution",
  "resource_id": "res_123",
  "created_at": "2026-08-26T12:00:00Z"
}
```

### Webhooks do cliente

```text
POST /v1/webhooks/{endpoint_id}
```

O produto deve padronizar eventos próprios:

- `message.received`;
- `message.accepted`;
- `message.sent`;
- `message.delivered`;
- `message.read`;
- `message.failed`;
- `instance.created`;
- `instance.qr_updated`;
- `instance.connected`;
- `instance.disconnected`;
- `rental.suspended`;
- `rental.expired`.

## 7. Modelo de chaves e segurança

### Chaves do cliente

Formato recomendado:

```text
mb_live_<tenant>_<random-secret>
```

Regras:

- mostrar o segredo apenas uma vez;
- armazenar somente hash;
- permitir múltiplas chaves por projeto;
- permitir ativar, desativar e revogar;
- registrar último uso sem gravar cada mensagem na auditoria;
- limitar por origem, tenant, projeto e recurso;
- suportar rotação sem interromper a chave antiga imediatamente;
- nunca usar a chave do provedor como chave do cliente.

### Segredos do provedor

- Evolution API key em cofre de segredos;
- token da instância criptografado em repouso;
- credenciais MySQL/Redis fora do código;
- chaves Meta/BSP em secrets manager;
- rotação documentada;
- acesso somente pelo worker autorizado;
- nenhum segredo em resposta de API ou log.

### Autorização

RBAC mínimo:

```text
platform_owner
platform_operator
tenant_owner
tenant_admin
tenant_developer
tenant_billing
tenant_readonly
```

Todo acesso deve validar:

```text
user → tenant → project → rental → resource
```

Nunca confiar apenas em `project_id` enviado pelo cliente.

### Proteções obrigatórias

- MFA para administradores;
- cookies HttpOnly e Secure;
- proteção CSRF no painel;
- rate limit de login;
- bloqueio progressivo contra brute force;
- request ID;
- logs estruturados;
- headers de segurança;
- validação de assinatura de webhook;
- allowlist de IP para operações administrativas;
- idempotência em criação, envio e cobrança;
- auditoria append-only;
- backups criptografados e testados.

## 8. Isolamento multi-tenant

Cada registro de negócio deve possuir `tenant_id`.

Tabelas fundamentais:

```text
tenants
tenant_users
projects
subscriptions
rentals
resources
provider_connections
api_keys
webhook_endpoints
messages
message_events
usage_counters
invoices
audit_events
```

Regras:

- toda query de negócio filtra por tenant;
- toda fila carrega tenant, projeto e recurso;
- todo webhook é validado pelo recurso esperado;
- um tenant nunca lista chaves ou instâncias de outro;
- o operador da plataforma deve ter auditoria reforçada;
- dados e mídia devem ter prefixo de tenant;
- backups devem permitir restauração seletiva quando possível.

## 9. Segurança e estabilidade da Evolution

A Evolution deve ser tratada como um provedor interno de alto impacto.

### Correções imediatas

- remover publicação direta da porta 4348;
- deixar acesso somente pelo proxy interno;
- confirmar a API key efetivamente usada pela instalação;
- instalar healthcheck;
- definir limites de CPU, memória e PIDs;
- monitorar o banco MySQL remoto;
- configurar timeout separado para conexão, leitura e escrita;
- implementar retry somente para erros transitórios;
- aplicar circuit breaker;
- não reiniciar globalmente por falha de uma instância;
- backup dos volumes `/evolution/instances` e `/evolution/store`;
- backup consistente do banco remoto;
- testar restauração de uma instância.

### Isolamento de recursos

Para poucos clientes, uma Evolution compartilhada pode ser usada com separação lógica.

Para clientes maiores ou de maior risco:

- instância Evolution dedicada;
- Redis dedicado ou namespace isolado;
- volume dedicado;
- banco separado ou schema separado;
- limite de mensagens próprio;
- política de manutenção própria.

## 10. Webhooks e carga

O webhook deve seguir este fluxo:

```text
Evolution/Meta
   ↓ HTTPS + assinatura
Webhook ingress
   ↓ validação mínima e deduplicação
Fila durável
   ↓ resposta 200 imediata
Workers
   ↓
Normalização, billing, automação e entrega ao cliente
```

O handler não deve:

- chamar IA antes de responder;
- consultar muitos bancos antes de responder;
- enviar mensagem de resposta antes de responder ao webhook;
- baixar mídia pesada no request;
- depender da central de licenças para cada evento.

Metas iniciais de engenharia:

- p50 do ingress menor que 100 ms;
- p95 menor que 250 ms;
- menos de 1% acima de 1 segundo;
- resposta 2xx rápida e idempotente;
- fila durável;
- retry com backoff;
- dead-letter queue;
- replay manual de evento;
- retenção e anonimização configuráveis.

Essas metas seguem a orientação publicada por provedores oficiais para webhooks rápidos e processamento assíncrono. [360dialog Webhooks](https://docs.360dialog.com/docs/messaging/webhook)

## 11. Métricas comerciais e técnicas

### Métricas por recurso

- estado da conexão;
- tempo desde último evento;
- reconexões por hora;
- QR gerado;
- mensagens aceitas;
- mensagens falhadas;
- latência de envio;
- eventos recebidos;
- webhooks entregues;
- webhooks em retry;
- fila pendente;
- uso de CPU/memória;
- tamanho de sessão e mídia.

### Métricas por tenant

- mensagens por período;
- destinatários únicos;
- taxa de erro;
- taxa de webhook;
- consumo do plano;
- excedentes;
- inadimplência;
- número de recursos;
- tickets e incidentes.

### Métricas para proteger números

- pico de mensagens por número;
- destinatários novos por 24 horas;
- mensagens sem opt-in registrado;
- bloqueios e respostas negativas;
- falhas repetidas;
- comportamento fora do padrão;
- reconexões anormais;
- qualidade do número quando o provedor oficial fornecer esse dado.

O sistema deve suspender ou reduzir velocidade antes de uma situação de risco, com aviso para o cliente e registro de motivo.

## 12. Planos comerciais sugeridos

Os planos não devem prometer apenas “quantidade de mensagens”. Devem combinar recurso, suporte, limites e isolamento.

### Start

- 1 recurso Evolution;
- 1 projeto;
- limite baixo de mensagens;
- webhook padrão;
- retenção curta;
- suporte comercial básico.

### Pro

- até 5 recursos;
- filas e webhooks assinados;
- métricas detalhadas;
- maior limite de uso;
- rotação de chaves;
- suporte prioritário.

### Business

- recursos dedicados ou isolados;
- quotas negociadas;
- SLA;
- backup e restauração assistidos;
- suporte técnico;
- integração personalizada.

### Official

- somente após integração Meta/BSP;
- WABA e número oficial;
- templates;
- onboarding oficial;
- limites e cobrança do provedor;
- qualidade e políticas oficiais.

Nunca misturar o plano “Evolution” com o plano “Official” na mesma promessa comercial.

## 13. Billing e aluguel

Estados do aluguel:

```text
requested
provisioning
awaiting_connection
active
past_due
suspended
expiring
expired
cancelled
destroyed
```

Regras:

- pagamento confirmado antes de ativar recurso pago;
- aluguel tem início, renovação e vencimento;
- suspensão não apaga dados imediatamente;
- cancelamento possui período de retenção;
- destruição exige confirmação e auditoria;
- toda cobrança usa idempotency key;
- webhook de pagamento é assinado e deduplicado;
- status comercial não deve apagar estado técnico sem processo explícito.

O modelo atual já possui planos, trials e integração Ciabra, mas ainda precisa separar formalmente `subscription`, `rental`, `resource` e `provider_connection`.

## 14. Caminho para API oficial

O produto oficial exigirá uma trilha própria:

1. Criar/verificar Business Portfolio.
2. Criar aplicativo Meta.
3. Configurar produto WhatsApp.
4. Definir modelo de onboarding dos clientes.
5. Avaliar Meta Tech Provider ou parceiro/BSP.
6. Implementar Embedded Signup ou onboarding equivalente.
7. Armazenar WABA, phone number ID e tokens com segurança.
8. Implementar templates e status.
9. Implementar webhooks de mensagens, status, erros e qualidade.
10. Implementar limites de mensagens e alertas.
11. Implementar cobrança e conciliação.
12. Passar por revisão, aprovação e requisitos legais.

O 360dialog informa que Tech Providers precisam completar etapas de empresa, aplicativo, verificação, aprovação e solução de parceiro; isso confirma que a linha oficial é um produto regulado pelo ecossistema Meta, não apenas um endpoint adicional. [Guia Tech Provider](https://docs.360dialog.com/partner/get-started/tech-provider-program/becoming-a-meta-tech-provider-a-step-by-step-guide)

## 15. Roadmap de implementação

### Fase 0 — segurança e estabilização

- corrigir autenticação e sessão do painel;
- remover defaults inseguros;
- proteger a porta da Evolution;
- healthchecks;
- limites de container;
- backups;
- logs e request ID;
- rate limits;
- métricas mínimas.

### Fase 1 — produto Evolution alugado

- criar `tenant_id` em todas as entidades;
- separar cliente, projeto, aluguel e recurso;
- criar API key por projeto;
- criar adapter Evolution;
- provisionar instância via fluxo controlado;
- conectar QR/pairing;
- normalizar mensagens e eventos;
- fila de webhooks;
- dashboard de uso;
- suspensão por vencimento;
- documentação pública.

### Fase 2 — operação profissional

- ambiente de homologação;
- load tests reproduzíveis;
- fila durável;
- dead-letter queue;
- replay de eventos;
- alertas;
- status page;
- runbooks;
- backup/restore automatizado;
- plano Business dedicado.

### Fase 3 — linha oficial

- decisão Meta Cloud API versus BSP;
- cadastro como parceiro/Tech Provider, se aplicável;
- Embedded Signup;
- adapter oficial;
- WABA/phone number lifecycle;
- templates;
- qualidade e limites;
- billing oficial;
- produto “Official” separado.

## 16. Critérios para considerar o produto profissional

O produto só deve ser considerado pronto para venda ampla quando atender a todos estes pontos:

- cada cliente isolado por tenant;
- cada recurso com proprietário e estado;
- cada chave revogável e rotacionável;
- nenhum cliente acessa a Evolution diretamente;
- webhook assinado e assíncrono;
- fila durável e replayável;
- rate limit e quotas;
- métricas por tenant e recurso;
- alertas em tempo real;
- backup testado;
- upgrade com homologação;
- teste de carga aprovado;
- cobrança idempotente;
- trilha de auditoria;
- documentação de integração;
- termos de uso, privacidade e política de abuso;
- separação explícita entre Evolution e API oficial.

## 17. Veredito

A base atual é suficiente para iniciar a construção do produto Evolution alugado, porque já existem licença, painel, Mago Bot, integração real, Redis, banco, instâncias e cobrança inicial.

Ela ainda não é suficiente para prometer uma “API equivalente à oficial” em segurança, estabilidade, conformidade ou escala.

O caminho profissional é:

1. consolidar a Evolution como provedor interno;
2. criar uma camada própria de API e aluguel;
3. transformar licenças em recursos de produto, não apenas tokens;
4. adicionar isolamento, filas, métricas, quotas e cobrança;
5. manter a linha Evolution claramente identificada;
6. construir em paralelo a linha oficial através da Meta ou de um parceiro oficial.

Esse desenho permite começar com o que já existe sem comprometer a futura integração oficial.
