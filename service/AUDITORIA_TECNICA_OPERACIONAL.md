# Auditoria técnica e operacional

Data da auditoria: 26/08/2026  
Escopo: central de licenças, instalação real da Evolution API no servidor, integração com o Mago Bot, capacidade observada e preparação para carga.

## 1. Conclusão executiva

O repositório atual (`licensing.mago-bot.com`) não contém a Evolution API. Ele contém uma central de licenças em FastAPI, independente do Mago Bot e da Evolution.

No servidor existe uma instalação separada e ativa:

- Evolution API: `evoapicloud/evolution-api:v2.3.7`
- Container: `evolution_api`
- Porta do host: `4348`
- Domínio configurado: `evoep.mago-bot.com`
- Mago Bot: `/www/wwwroot/magobot.phpd77.com`
- Central de licenças: `/www/wwwroot/licensing.mago-bot.com/service`
- Evolution Redis: `redis:7-alpine`
- Banco configurado na Evolution: MySQL remoto, banco `magopix_pro`
- Webhook global: `https://magobot.phpd77.com/webhooks/evolution`

Estado atual:

- a Evolution está instalada e respondendo;
- o endpoint raiz informa a versão `2.3.7`;
- não houve restart do container desde a inicialização observada;
- existem duas instâncias WhatsApp ativas no banco do Mago Bot;
- o sistema tem cache Redis, deduplicação e métricas internas básicas;
- não existe uma medição de carga de produção suficiente para declarar capacidade segura;
- não existem limites de CPU, memória ou PIDs nos containers;
- o serviço não está preparado para uma carga comercial crítica sem reforços.

## 2. Evidências verificadas

As verificações foram somente de leitura. Não foram criadas instâncias, enviadas mensagens, alteradas configurações ou reiniciados containers.

### 2.1 Central de licenças

Arquivos principais:

- `app/main.py`: FastAPI, startup, criação automática de tabelas e planos.
- `app/routes/licenses.py`: emissão, validação, listagem e revogação.
- `app/routes/product.py`: planos, trials e compatibilidade das rotas.
- `app/routes/account.py`: login e usuários do painel.
- `app/routes/health.py`: health check superficial.
- `app/db.py`: pool SQLAlchemy.
- `docker-compose.yml`: app + PostgreSQL.

Configuração observada:

- Gunicorn com 4 workers Uvicorn.
- Pool SQLAlchemy de 20 conexões e até 40 conexões extras por processo.
- PostgreSQL 16 separado.
- Porta publicada diretamente no host em `0.0.0.0:4349`.
- Sem Redis, fila, Prometheus ou worker assíncrono.
- Sem testes automatizados no repositório.

Risco de capacidade: o pool configurado em `db.py` é por processo. Com 4 workers, a capacidade teórica pode chegar a aproximadamente 240 conexões SQLAlchemy (`20 + 40` por worker), antes de considerar outros serviços. Isso é muito superior ao que o PostgreSQL normalmente deveria aceitar sem configuração e testes específicos.

Além disso, cada validação de licença faz consulta, atualização de `last_used_at`, grava auditoria e executa commit. Esse padrão é inadequado para validar em cada mensagem ou evento de WhatsApp.

### 2.2 Evolution API

Container observado:

```text
image: evoapicloud/evolution-api:v2.3.7
status: running
restart policy: always
restart count: 0
OOM killed: false
healthcheck: inexistente
```

Imagem observada:

```text
digest: sha256:1bd8afc4a6cf48822e6cf02469aeae7bd35a12a6b616eacd1291926307f4d339
created: 2025-12-05
```

Volumes:

- `/evolution/instances`
- `/evolution/store`

Configuração funcional observada:

- `DATABASE_ENABLED=true`
- `DATABASE_PROVIDER=mysql`
- `CACHE_REDIS_ENABLED=true`
- Redis apontando para `redis:6379/0`
- webhook global habilitado
- webhook global configurado para `https://magobot.phpd77.com/webhooks/evolution`
- eventos globais não estão configurados para entrega por evento individual (`WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false`)
- versão de WhatsApp informada pelo endpoint: `2.3000.1046041993`

O stack Compose de `/www/wwwroot/magobot.phpd77.com` contém PostgreSQL e Redis para o Mago Bot, mas não contém a Evolution API. A Evolution está em outro stack/rede (`mago-evolution_default`). Portanto, a configuração declarada no Compose do Mago Bot não é a instalação real da Evolution.

O banco da Evolution foi identificado como:

```text
mysql://<credenciais>@173.212.215.60:3306/magopix_pro
```

As credenciais foram deliberadamente omitidas deste documento.

### 2.3 Mago Bot

O Mago Bot possui duas camadas:

- Flask/Gunicorn na porta interna 8000, publicado no host como 8002.
- FastAPI/Uvicorn na porta 8010 para webhooks e métricas.

Container observado para a API FastAPI:

```text
uvicorn app_fastapi.main:app --host 0.0.0.0 --port 8010
```

Container observado para o app Flask:

```text
gunicorn -b 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120 wsgi:app
```

O fluxo do webhook Evolution é síncrono do ponto de vista da requisição HTTP: o endpoint recebe o JSON, entra em contexto Flask e executa `evolution_webhook_logic` antes de devolver a resposta. Existem chamadas externas e operações de banco no fluxo. Isso significa que o webhook pode acumular latência e consumir workers sob carga.

Integração com Evolution:

- `requests.Session` compartilhada.
- Pool HTTP de 50 conexões para HTTP e 50 para HTTPS.
- Timeout de 30 segundos por chamada.
- Sem retry automático com backoff.
- Sem circuit breaker.
- Sem limite de mensagens por instância.
- Uso de token administrativo para operações de gestão.
- Uso de token da instância para envio de mensagens.

O código possui proteções úteis:

- deduplicação Redis para alguns eventos;
- locks distribuídos com `SET NX` e expiração;
- cache de QR/pairing code;
- cache de telefones ativos por 300 segundos;
- métricas internas de duração;
- testes e script de carga de webhook.

Essas proteções melhoram a base, mas não substituem fila, backpressure, rate limit, retry controlado e observabilidade persistente.

## 3. Estado da versão da Evolution API

O container instalado é `v2.3.7`.

Na fonte oficial consultada, a linha 2.3.7 aparece como versão do projeto e o `package.json` oficial também declara `2.3.7`. A documentação oficial informa suporte a Node.js 20+, PostgreSQL ou MySQL, Redis, autenticação por cabeçalho `apikey`, tokens por instância, validação de assinatura de webhook e opções de mensageria/eventos.

Conclusão sobre atualização:

- a versão instalada é reconhecida e coerente com a linha oficial 2.3.7;
- não existe neste servidor um mecanismo de atualização automática ou pinagem documentada de digest;
- não há ambiente de homologação para testar upgrade;
- não é seguro atualizar diretamente em produção por causa das sessões WhatsApp persistidas;
- o upgrade deve ser feito com backup dos volumes, backup do banco, janela de manutenção e teste de reconexão.

Fonte oficial: [repositório Evolution API](https://github.com/evolution-foundation/evolution-api), [package.json oficial](https://github.com/evolution-foundation/evolution-api/blob/main/package.json) e [Compose oficial](https://github.com/evolution-foundation/evolution-api/blob/main/docker-compose.yaml).

## 4. Exposição e segurança da instalação real

### 4.1 Porta pública

A porta `4348` está publicada em todas as interfaces do host (`0.0.0.0` e IPv6). O Nginx também faz proxy público de `evoep.mago-bot.com` para `127.0.0.1:4348`.

Recomendação:

- publicar somente via Nginx/HTTPS;
- remover o bind público do Docker e usar `127.0.0.1:4348:8080`;
- bloquear acesso direto por firewall;
- restringir o endpoint à API do Mago Bot e aos administradores autorizados.

### 4.2 Autenticação

O endpoint `/instance/fetchInstances` respondeu `401 Unauthorized`, portanto as rotas de gestão exigem autenticação.

O endpoint raiz respondeu publicamente com versão, documentação e manager. Isso é aceitável como descoberta mínima, mas deve ser avaliado se a política for ocultar informações de versão.

No ambiente do container não foi encontrada uma variável `AUTHENTICATION_API_KEY` explícita; a autenticação pode estar sendo resolvida por configuração compatível da imagem ou por outro mecanismo da versão instalada. Isso precisa ser confirmado no `.env` real e na documentação da imagem antes de qualquer venda.

### 4.3 Segredos

Foram encontrados arquivos `.env` com permissões de leitura ampla para o usuário do site no projeto do Mago Bot (`-rw-r--r--`). O conteúdo não foi copiado para este documento.

Ações necessárias:

- usar permissões `600` nos `.env`;
- garantir que o usuário do processo consiga ler sem tornar o arquivo público;
- rotacionar chaves que tenham sido expostas em logs, chats, backups ou arquivos compartilhados;
- remover valores padrão como `change-me` dos Compose;
- usar Docker secrets ou um cofre de segredos;
- não armazenar chaves privadas de pagamento em diretórios servidos pelo site.

## 5. Carga atual observada

Snapshot do servidor no momento da auditoria:

- 6 vCPUs;
- 11 GiB de RAM;
- aproximadamente 5,8 GiB disponíveis;
- sem swap;
- disco de 193 GiB, aproximadamente 43% utilizado;
- Evolution API: aproximadamente 192 MiB;
- Evolution Redis: aproximadamente 63 MiB;
- central de licenças: aproximadamente 270 MiB;
- PostgreSQL da central: aproximadamente 39 MiB.

Esses números são fotografia instantânea, não capacidade máxima.

Banco do Mago Bot:

- `message_logs`: 33.886 linhas;
- `whatsapp_instances`: 2 linhas ativas;
- banco total: aproximadamente 26 MiB;
- tabela `message_logs`: aproximadamente 17 MiB.

Redis da Evolution:

- Redis 7.4.8;
- aproximadamente 60 MiB utilizados;
- sem pressão de memória no momento;
- sem taxa significativa de comandos no instante consultado.

Não há limites de CPU, memória ou PIDs configurados nos containers. Portanto, um pico em um serviço pode competir com os demais e prejudicar a estabilidade de todo o servidor.

## 6. Qual carga está comprovadamente suportada?

Nenhuma carga de produção foi comprovada por teste neste servidor.

Existe um script de teste em:

```text
/www/wwwroot/magobot.phpd77.com/tools/load_test_webhooks.py
```

O padrão do script é:

- 50 threads concorrentes;
- 2.000 requisições;
- timeout de 10 segundos;
- destino `/webhooks/evolution`.

Esse script é um teste de webhook sintético. Ele não comprova capacidade de:

- conexões WhatsApp simultâneas;
- envio de mensagens;
- recebimento de mídia;
- reconexões;
- QR code e pairing code;
- múltiplos clientes;
- pico de webhooks reais;
- uso combinado de banco, Redis e Evolution.

Estimativa conservadora para o estado atual, sem teste formal:

| Área | Capacidade segura declarada |
|---|---:|
| Instâncias WhatsApp reais | 2 observadas, sem limite técnico formal |
| Webhooks síncronos | não declarar acima de teste controlado |
| Concorrência de teste disponível | 50 threads / 2.000 requests no script |
| Mensagens por segundo | não medido |
| Validações de licença | não declarar; há escrita síncrona por chamada |
| Clientes comerciais isolados | não comprovado |

Qualquer número maior seria especulação. Para vender capacidade, deve existir teste reproduzível com critérios de aprovação.

## 7. Principais gargalos para carga

### Crítico

1. Webhook executa lógica de negócio antes de responder.
2. Chamadas externas possuem timeout de até 30 segundos.
3. Não há retry com backoff nem circuit breaker.
4. Não há limites de recursos nos containers.
5. A central de licenças grava auditoria em cada validação.
6. Não há métricas persistentes nem alertas.
7. Não há teste de carga de instâncias WhatsApp.
8. O banco da Evolution está remoto, criando dependência de rede.

### Alto

1. O container da Evolution não tem healthcheck.
2. O health check do Mago Bot não verifica banco ou Redis.
3. Não há fila para desacoplar recebimento e processamento.
4. O pool HTTP é fixo em 50 conexões e sem métricas de saturação.
5. O timeout de 30 segundos pode bloquear threads em falhas da Evolution.
6. Não há limite por cliente, instância, número ou plano.
7. Não há política de retenção para `message_logs`.
8. Não há swap no servidor.

## 8. Risco específico de derrubar números conectados

A central de licenças não deve participar do caminho crítico de cada mensagem. O desenho seguro é:

```text
Conexão WhatsApp
      ↓
Evolution API
      ↓
Mago Bot / fila de eventos
      ↓
Cache local de licença
      ↓
Central de licenças apenas para sincronização e decisão de acesso
```

Regras recomendadas:

- validar licença ao iniciar ou renovar uma sessão;
- manter cache local por período curto e explícito;
- usar circuit breaker na central;
- permitir tolerância controlada quando a central estiver temporariamente indisponível;
- não revogar uma sessão já conectada por uma falha transitória de rede;
- aplicar revogação em nova conexão, renovação ou operação sensível;
- processar webhooks em fila;
- limitar mensagens por instância;
- separar reconexão, envio e recebimento em filas distintas;
- nunca reiniciar todas as instâncias por causa de uma falha de licença de um único cliente.

## 9. Plano mínimo antes de carga comercial

### P0

- Fixar limites de CPU e memória por container.
- Adicionar healthchecks da Evolution, Redis e bancos.
- Remover exposição direta da porta 4348.
- Confirmar e rotacionar todas as chaves da Evolution.
- Adicionar rate limit no Mago Bot e na central.
- Colocar webhook em fila com resposta rápida.
- Implementar retry com backoff e circuit breaker.
- Criar cache de licença com TTL e modo de contingência.
- Proteger o endpoint de auditoria/validação contra gravação por evento excessivo.
- Configurar alertas de CPU, memória, Redis, banco, latência e erro.

### P1

- Criar ambiente de homologação.
- Testar upgrade da Evolution em cópia dos volumes.
- Testar reconexão e persistência das duas instâncias.
- Criar teste de carga com webhooks reais anonimizados.
- Criar teste de envio limitado para número de teste.
- Medir p50, p95, p99, erros, fila e tempo de processamento.
- Criar política de retenção e particionamento de mensagens.
- Separar banco da Evolution do banco comercial do Mago Bot.

### P2

- Escalar horizontalmente o consumidor de webhooks.
- Usar Redis dedicado para a Evolution e Redis dedicado para o Mago Bot.
- Usar fila persistente para mensagens e eventos.
- Adicionar status page e runbooks.
- Criar quotas comerciais por cliente e instância.
- Criar módulo futuro de aluguel com inventário, cobrança e isolamento.

## 10. Critério de aprovação de carga

Antes de afirmar capacidade, executar testes em homologação com:

1. 2 instâncias, depois 5, 10 e 20.
2. Picos de webhook de 10, 25, 50 e 100 requisições por segundo.
3. Envio controlado para números de teste.
4. Simulação de Redis indisponível.
5. Simulação de banco remoto lento.
6. Reinício do Mago Bot.
7. Reinício da Evolution.
8. Expiração e revogação de licença.
9. Falha da central de licenças.
10. Observação de 30 minutos após cada cenário.

Critérios mínimos:

- nenhum número perde sessão por falha transitória da central;
- zero perda silenciosa de webhook;
- p95 de webhook abaixo do limite definido;
- fila retorna a zero depois do pico;
- banco não ultrapassa 70% de conexões;
- Redis não apresenta bloqueios;
- memória não cresce continuamente;
- nenhum container é encerrado por OOM;
- erro de envio e reconexão é rastreável por instância.

## 11. Veredito final

O sistema está funcional e já existe uma integração real entre Mago Bot e Evolution API. A instalação não é fictícia nem apenas documentação.

Porém, a capacidade real ainda é de pequena operação controlada. Hoje é razoável tratar como:

- Evolution: operação ativa de pequena escala;
- Mago Bot: aplicação funcional com mecanismos básicos de cache e deduplicação;
- Licensing: MVP funcional, não componente de alta disponibilidade;
- carga comercial: ainda não comprovada;
- expansão para muitos números/clientes: requer fila, métricas, limites e testes;
- aluguel de API oficial: ainda não implementado.

Não declarar número máximo de instâncias, mensagens por segundo ou clientes suportados antes de executar o plano de teste acima.

