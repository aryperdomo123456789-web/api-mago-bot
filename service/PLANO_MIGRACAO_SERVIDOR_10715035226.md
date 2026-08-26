# Plano profissional de migração para o servidor 107.150.35.226

Data: 26/08/2026  
Objetivo: migrar e estruturar a plataforma em dois sites separados, com controle administrativo centralizado:

1. site público do produto;
2. site privado de administração da API, licenças, aluguéis e Evolution.

## 1. Arquitetura proposta

### Site público do produto

Domínio sugerido:

```text
app.mago-bot.com
```

Também pode ser usado:

```text
produto.mago-bot.com
```

Responsabilidades:

- landing page;
- cadastro de clientes;
- login do cliente;
- planos;
- trials;
- contratação;
- documentação pública;
- criação de projeto;
- visualização de aluguel;
- geração/visualização controlada de API key;
- conexão da instância por QR ou pairing;
- uso da API;
- métricas do cliente;
- faturamento;
- suporte.

Esse site nunca deve expor:

- token global da Evolution;
- credenciais do banco;
- painel interno da Evolution;
- chaves de outros clientes;
- rotas administrativas da plataforma.

### Site privado da API

Domínio sugerido:

```text
control.mago-bot.com
```

Alternativas:

```text
admin-api.mago-bot.com
licensing.mago-bot.com
```

Responsabilidades:

- login administrativo;
- MFA;
- gestão de tenants;
- clientes e organizações;
- planos e preços;
- aluguéis;
- provisionamento de recursos;
- licenças e API keys;
- Evolution API;
- instâncias;
- estados de conexão;
- limites e quotas;
- métricas globais;
- auditoria;
- cobrança;
- suspensão e encerramento;
- operações de suporte.

Esse site deve ser restrito por:

- autenticação forte;
- MFA;
- allowlist de IP quando possível;
- VPN ou acesso administrativo separado;
- roles e permissões;
- logs de auditoria;
- nenhuma indexação pública.

## 2. Relação entre os dois sites

```text
Cliente
  │
  └── app.mago-bot.com
          │ login, contratação e uso
          ▼
      API da plataforma
          │ valida tenant, plano, aluguel e chave
          ▼
      control.mago-bot.com
          │ operações internas
          ├── Licensing Service
          ├── Rental Service
          ├── Billing Service
          └── Provider Orchestrator
                    │
                    ▼
             Evolution API
```

O site público nunca deve chamar a Evolution diretamente. Ele chama a API da nossa plataforma, que verifica:

```text
usuário → tenant → projeto → aluguel → recurso → quota → API key
```

## 3. Estado real do servidor novo

Auditoria somente de leitura realizada via SSH:

- hostname: `s303895.wholesaleinternet.net`;
- 16 vCPUs;
- 62 GiB de RAM;
- aproximadamente 60 GiB disponíveis;
- 8 GiB de swap;
- disco de 252 GiB;
- aproximadamente 220 GiB livres;
- aaPanel instalado;
- Nginx instalado;
- MariaDB escutando em `0.0.0.0:3306`;
- Docker não instalado no momento da auditoria;
- já existem sites em `/www/wwwroot`.

### Atualização de verificação em 26/08/2026

Os dois sites foram criados no aaPanel:

```text
/www/wwwroot/app.mago-bot.com
/www/wwwroot/evo-api.mago-bot.com
```

Foi confirmado:

- `app.mago-bot.com` resolve para `107.150.35.226`;
- `evo-api.mago-bot.com` resolve para `107.150.35.226`;
- os dois virtual hosts existem no Nginx e Apache do aaPanel;
- os dois sites possuem configuração SSL criada;
- Docker Engine `26.1.4` está instalado;
- `docker-compose` `v2.27.1` está disponível;
- não existe ainda o comando `docker compose` como plugin separado, mas o binário `docker-compose` atende à primeira implantação;
- não existem containers ou imagens Docker no servidor nesse momento;
- os dois diretórios estão vazios;
- os domínios retornam `403` porque ainda não há aplicação publicada no document root/proxy.

Conclusão: a camada de DNS, sites, SSL, Nginx e Docker está pronta para receber a implantação. Ainda falta subir a aplicação pública, a API de controle, a Evolution, os bancos e o Redis.

### Bloqueio de segurança identificado

A porta `3306` está publicada em todas as interfaces. Antes de usar esse MariaDB ou instalar novos bancos:

- restringir MariaDB para `127.0.0.1` ou rede privada;
- bloquear 3306 no firewall externo;
- permitir somente IPs necessários;
- usar usuários de banco sem privilégios globais;
- exigir senha forte;
- ativar TLS quando houver conexão remota;
- revisar usuários existentes.

Não iniciar migração de dados antes de corrigir isso.

## 4. Evolution API versus Evolution Go

### Evolution API tradicional

É a escolha recomendada para a primeira implantação neste servidor porque:

- o Mago Bot atual já usa esse contrato;
- a integração existente possui `EvolutionService`;
- já há fluxo de instância, QR, pairing, envio e webhook;
- já existe experiência operacional com a imagem Docker;
- suporta Baileys e Meta Cloud API;
- possui Redis, banco, eventos, mídia e integrações amplas;
- é o caminho com menor risco de migração.

A documentação oficial descreve a Evolution API como a API REST principal, com Node.js/TypeScript, Baileys, Meta Cloud API, multi-tenant por instância, Redis, PostgreSQL/MySQL, Docker, eventos e armazenamento de mídia. [Documentação oficial Evolution API](https://docs.evolutionfoundation.com.br/evolution-api)

### Evolution Go

O Evolution Go é uma implementação em Go/whatsmeow focada em alta performance e menor consumo de recursos.

A documentação oficial informa suporte a:

- Go 1.24+;
- PostgreSQL opcional;
- WebSocket;
- QR code;
- mídia;
- Swagger/OpenAPI;
- webhooks;
- RabbitMQ/AMQP;
- NATS;
- MinIO/S3.

Fonte: [Documentação oficial Evolution Go](https://docs.evolutionfoundation.com.br/evolution-go)

### Recomendação

Não substituir a Evolution API pela Evolution Go no primeiro corte de produção.

Usar esta sequência:

1. Migrar a Evolution API tradicional.
2. Estabilizar o produto e as duas aplicações.
3. Criar ambiente de homologação da Evolution Go.
4. Executar testes de contrato contra o adapter interno.
5. Comparar QR, pairing, conexão, webhook, mídia, grupos e envio.
6. Medir memória, CPU, latência e recuperação.
7. Migrar apenas clientes/instâncias de teste.
8. Manter rollback para Evolution API tradicional.

O produto deve falar com um `ProviderAdapter`, não diretamente com endpoints específicos:

```text
EvolutionAdapter
EvolutionGoAdapter
OfficialCloudAdapter
```

Assim, a troca futura não exige reescrever o site público.

## 5. Instalação recomendada no novo servidor

### Camada 1 — preparação do sistema

- atualizar o sistema operacional;
- criar usuário operacional sem uso diário de root;
- manter SSH por chave;
- trocar a senha root depois da validação da chave;
- configurar firewall;
- bloquear portas não utilizadas;
- corrigir exposição do MariaDB;
- instalar Docker Engine e Docker Compose Plugin;
- configurar rotação de logs;
- configurar timezone e NTP;
- instalar monitoramento do host.

### Camada 2 — domínios no aaPanel

Criar dois sites separados:

```text
app.mago-bot.com
control.mago-bot.com
```

Para cada site:

- diretório próprio;
- certificado SSL próprio;
- logs próprios;
- proxy reverso próprio;
- `.env` próprio;
- usuário e permissões próprios;
- backup próprio.

Criar também um terceiro endpoint técnico, sem painel público:

```text
evolution-api.mago-bot.com
```

Esse endpoint será usado pela plataforma internamente. A página de gestão da Evolution não deve ficar aberta ao público geral.

### Camada 3 — rede Docker

Criar redes separadas:

```text
platform_frontend
platform_backend
evolution_internal
observability
```

Regra:

- Nginx fala com portas HTTP internas;
- site público fala com API da plataforma;
- API da plataforma fala com Evolution;
- banco não é publicado;
- Redis não é publicado;
- Evolution não é publicada diretamente em uma porta ampla do host.

## 6. Serviços do primeiro stack

```text
public_app
control_api
control_worker
evolution_api
evolution_redis
platform_postgres
evolution_database
minio ou S3
redis_platform
prometheus
grafana
```

Para a primeira versão, `public_app` e `control_api` podem compartilhar o mesmo código em processos separados, mas devem ter:

- configurações diferentes;
- rotas públicas e privadas separadas;
- logs separados;
- permissões diferentes;
- limites de recursos diferentes.

## 7. Banco de dados

Não usar um único banco para tudo.

### Banco da plataforma

Responsável por:

- tenants;
- usuários;
- projetos;
- planos;
- subscriptions;
- rentals;
- API keys;
- quotas;
- invoices;
- auditoria;
- usage counters.

### Banco da Evolution

Responsável por:

- dados da Evolution;
- instâncias;
- mensagens configuradas para persistência;
- sessões conforme a configuração da versão;
- eventos do provedor.

### Regras

- usuários diferentes por banco;
- credenciais diferentes;
- backups diferentes;
- migrations diferentes;
- sem foreign key entre bancos;
- integração apenas por serviços/API/eventos.

### Banco personalizado do projeto e porta 33366

A porta `33366` está livre no servidor novo.

É possível usar um banco exclusivo do projeto nessa porta, mas a recomendação profissional é não publicar o banco na internet. A porta deve ser usada apenas como mapeamento local do host, se houver necessidade operacional.

Modelo recomendado com Docker:

```text
Host:      127.0.0.1:33366
Container: project-db:3306
Rede:      platform_backend
```

Dentro da rede Docker, os serviços devem acessar:

```text
project-db:3306
```

Não devem usar `33366` entre containers. `33366` é somente a porta externa/local do host.

Exemplo conceitual:

```yaml
services:
  project-db:
    image: mariadb:11
    ports:
      - "127.0.0.1:33366:3306"
    environment:
      MARIADB_DATABASE: platform_db
      MARIADB_USER: platform_user
      MARIADB_PASSWORD: usar-secret-forte
      MARIADB_ROOT_PASSWORD: usar-outro-secret-forte
```

Para este projeto, separar logicamente os bancos:

```text
platform_db   → site público, painel, clientes, planos, aluguéis e licenças
evolution_db  → dados da Evolution API
```

Mesmo que os dois bancos estejam no mesmo servidor ou container, devem possuir usuários separados e permissões mínimas.

Alternativa preferida quando todos os serviços estiverem no Docker:

```yaml
ports: []
```

Nesse modelo, o banco não tem porta publicada no host e só é acessível pela rede Docker. Para administração externa, usar túnel SSH:

```bash
ssh -L 33366:127.0.0.1:33366 root@107.150.35.226
```

Não alterar a porta `3306` do MariaDB já instalado no aaPanel sem inventariar os sites existentes, porque essa alteração pode derrubar aplicações que já dependem dela.

## 8. Controle administrativo dos acessos

O site privado será a autoridade de produto.

### Fluxo de criação

1. Cliente cria conta no site público.
2. Cliente escolhe plano.
3. Pagamento/trial é aprovado.
4. Plataforma cria tenant.
5. Plataforma cria projeto.
6. Plataforma cria aluguel.
7. Provisioning cria recurso Evolution.
8. Plataforma gera API key.
9. Cliente recebe somente a chave da nossa API.
10. Cliente conecta pelo QR/pairing no fluxo permitido.

### Fluxo de autorização de cada request

```text
API key
  ↓
hash da chave
  ↓
tenant/projeto
  ↓
aluguel ativo
  ↓
recurso permitido
  ↓
scope e quota
  ↓
adapter do provedor
```

### Suspensão

Quando houver vencimento ou violação:

- bloquear novas mensagens;
- preservar a sessão por tolerância configurada;
- informar o cliente;
- registrar motivo;
- não apagar imediatamente o recurso;
- permitir reativação após pagamento;
- destruir somente após retenção e confirmação.

## 9. Endpoints e domínios

### Público

```text
https://app.mago-bot.com/
https://app.mago-bot.com/docs
https://app.mago-bot.com/v1/auth
https://app.mago-bot.com/v1/plans
https://app.mago-bot.com/v1/rentals
https://app.mago-bot.com/v1/messages
https://app.mago-bot.com/v1/webhooks
```

### Controle administrativo

```text
https://control.mago-bot.com/
https://control.mago-bot.com/admin
https://control.mago-bot.com/v1/tenants
https://control.mago-bot.com/v1/licenses
https://control.mago-bot.com/v1/rentals
https://control.mago-bot.com/v1/resources
https://control.mago-bot.com/v1/audit
https://control.mago-bot.com/v1/metrics
```

### Evolution interna

```text
https://evolution-api.mago-bot.com/
```

Esse domínio deve ser acessível apenas pelo backend e por operações administrativas controladas. O cliente pode receber endpoints normalizados da nossa plataforma, mas não a chave global da Evolution.

## 10. Configuração essencial da Evolution

Na instalação nova, configurar explicitamente:

- `SERVER_URL` com o domínio técnico;
- `SERVER_PORT=8080` interno;
- `AUTHENTICATION_API_KEY` forte;
- `DATABASE_ENABLED=true`;
- `DATABASE_PROVIDER` definido conforme o banco escolhido;
- `DATABASE_CONNECTION_URI` sem credencial exposta;
- `DATABASE_CONNECTION_CLIENT_NAME` único;
- `CACHE_REDIS_ENABLED=true`;
- `CACHE_REDIS_URI` privado;
- `CACHE_REDIS_PREFIX_KEY` único;
- `CACHE_REDIS_SAVE_INSTANCES` conforme política de segurança;
- `WEBHOOK_GLOBAL_ENABLED=true`;
- `WEBHOOK_GLOBAL_URL` apontando para o ingress do Mago Bot;
- `WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=true` quando cada evento tiver rota/política própria;
- eventos de mensagem, conexão, QR e erro selecionados explicitamente;
- `CORS_ORIGIN` restrito;
- `CORS_CREDENTIALS=false` salvo necessidade comprovada;
- nível de logs controlado;
- telemetria avaliada e documentada;
- S3/MinIO para mídia quando o volume justificar.

A documentação oficial lista essas variáveis, incluindo banco, Redis, webhooks, CORS, eventos, API key, S3/MinIO e configurações de sessão. [Variáveis de ambiente oficiais](https://docs.evolutionfoundation.com.br/evolution-api/configuration/env)

## 11. Migração de dados e instâncias

Não copiar a produção diretamente para o novo servidor sem inventário.

### Ordem segura

1. Inventariar domínios, DNS, SSL e portas.
2. Fazer backup da central de licenças.
3. Fazer backup do banco do Mago Bot.
4. Fazer backup do banco da Evolution.
5. Fazer backup dos volumes de instâncias e store.
6. Registrar cada instância, estado, telefone e último evento.
7. Instalar stack novo em homologação.
8. Restaurar bancos em nomes diferentes.
9. Restaurar volumes em diretórios novos.
10. Validar integridade e permissões.
11. Subir primeiro com domínio de teste.
12. Testar QR, conexão, webhook e envio controlado.
13. Reduzir TTL DNS.
14. Fazer janela de corte.
15. Pausar alterações no servidor antigo.
16. Sincronizar dados finais.
17. Atualizar DNS.
18. Validar clientes e instâncias.
19. Manter o antigo em modo rollback.
20. Encerrar somente depois do período de segurança.

### O que não fazer

- não usar `docker compose down` no servidor antigo antes do corte;
- não apagar volumes;
- não copiar `.env` para chat ou documentação;
- não usar `latest` em produção;
- não trocar Evolution API por Evolution Go no mesmo corte;
- não alterar banco remoto sem backup;
- não expor PostgreSQL, MySQL ou Redis à internet.

## 12. Evolution Go em homologação

Criar um segundo projeto isolado:

```text
/opt/evolution-go-staging
```

Executar testes contra o contrato interno:

- criar instância;
- obter QR;
- conectar número de teste;
- receber `connection.update`;
- receber mensagem;
- enviar texto;
- enviar mídia;
- receber erro;
- reiniciar instância;
- apagar instância;
- restaurar sessão;
- emitir webhook assinado;
- validar documentação Swagger.

Só considerar migração quando todos os testes passarem e os números de teste sobreviverem a reinício e restauração.

## 13. Monitoramento obrigatório

Monitorar por site e por serviço:

- disponibilidade;
- latência p50/p95/p99;
- HTTP 4xx/5xx;
- fila;
- workers ocupados;
- Redis;
- banco;
- CPU;
- memória;
- disco;
- conexões Evolution;
- reconexões por instância;
- QR expirado;
- webhooks falhos;
- mensagens enviadas e falhas;
- licenças expiradas;
- inadimplência;
- incidentes.

Alertas mínimos:

- Evolution indisponível;
- banco acima de 70% de conexões;
- disco acima de 70%;
- memória acima de 75%;
- fila crescendo por 5 minutos;
- erro de webhook acima do limite;
- reconexões anormais;
- falhas de autenticação administrativas;
- falhas consecutivas do billing.

## 14. Cronograma sugerido

### Fase 1 — preparação

- escolher os dois domínios;
- apontar DNS;
- corrigir firewall e MariaDB;
- instalar Docker;
- criar backups;
- criar estrutura de diretórios.

### Fase 2 — infraestrutura

- subir bancos privados;
- subir Redis;
- instalar Evolution API;
- configurar SSL e proxy;
- validar API key;
- validar volumes;
- validar webhook.

### Fase 3 — produto

- migrar central de licenças;
- separar site público e controle administrativo;
- implementar tenant, rental e resource;
- ocultar Evolution do cliente;
- conectar billing;
- publicar documentação.

### Fase 4 — migração real

- migrar instâncias de teste;
- executar testes de carga;
- migrar clientes em lotes;
- manter rollback;
- acompanhar por 24–72 horas.

### Fase 5 — evolução

- Evolution Go em staging;
- adapter oficial Meta/BSP;
- memória e orquestração de conversas;
- voz, e-mail, SMS, RCS e atendimento.

## 15. Decisão final

Para este servidor, o plano recomendado é:

```text
Servidor 107.150.35.226
  ├── app.mago-bot.com             público/produto
  ├── control.mago-bot.com         privado/administração
  ├── evolution-api.mago-bot.com   interno/provedor
  ├── platform database            privado
  ├── evolution database           privado
  ├── Redis platform               privado
  └── Redis Evolution              privado
```

Escolha inicial:

> Evolution API tradicional em produção, Evolution Go somente em homologação até provar compatibilidade.

Essa decisão preserva a integração já existente, reduz o risco da migração e mantém aberta a evolução para Go e para a API oficial da Meta.
