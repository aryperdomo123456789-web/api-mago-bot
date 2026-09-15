# Auditoria de reaproveitamento: gentle-aid → Mago Bot

**Data:** 26 de agosto de 2026  
**Repositório analisado:** [aryperdomo123456789-web/gentle-aid](https://github.com/aryperdomo123456789-web/gentle-aid)  
**Referências locais:** `main` `4d4a5fe`, `backup` `679b125`, `audit-codex` `1c7a057`.

## Veredito executivo

O gentle-aid não deve ser mesclado como um produto inteiro no Mago Bot. Ele é um ecossistema diferente, focado em mídia para criadores, com React/TanStack/Flask/FFmpeg/yt-dlp, enquanto o Mago Bot é um control plane multi-tenant de API WhatsApp com FastAPI/PostgreSQL/Redis, providers isolados, outbox, workers, RBAC, quotas e tracing.

O valor real está em três padrões: **governança de chaves e health checks de providers**, **pipeline de transcrição com fallback e timestamps** e **runtime de jobs com heartbeat, cancelamento, auditoria e recuperação de órfãos**. Esses padrões aceleram a camada de IA do Mago Bot, mas devem ser reimplementados sobre PostgreSQL/Redis/outbox do Mago; não se deve copiar o cofre JSON, threads locais ou caminhos de filesystem do gentle-aid para produção multi-tenant.

## Inventário de branches

| Branch | Situação | Decisão |
|---|---|---|
| `origin/main` (`4d4a5fe`) | Linha principal, catálogo de APIs, jobs, transcrição, voz, radar e frontend completo. | Fonte de padrões e leitura de arquitetura. |
| `origin/backup` (`679b125`) | Snapshot aaPanel com rota de transcrição de vídeo e melhorias de histórico/status. | Extrair seletivamente a normalização e fallback; não fazer merge integral. |
| `origin/audit-codex` (`1c7a057`) | Grande divergência: cerca de 172 caminhos alterados, muitas remoções e `__pycache__` versionado. | Não mesclar; usar apenas como registro de decisões/auditoria. |

## O que já existe no gentle-aid

O catálogo `backend/app/services/api_keys.py` centraliza vários providers: DeepSeek, Gemini, Groq, OpenRouter, Mistral, SiliconFlow, Hugging Face, Cohere, Tavily, Exa, Firecrawl, Jina, Langfuse, Cloudflare, Whisper e outros. Ele tem metadados de categoria, documentação, variável de ambiente, formato esperado, método de autenticação, teste real e mensagem de remediação. O README informa que as chaves ficam em cofre fora do Git, são mascaradas e podem ser geridas por uma Central de APIs.

Isso é uma referência forte para uma futura **AI Provider Control Plane** do Mago. A diferença obrigatória é que o Mago deve guardar segredo criptografado no modelo de credenciais por tenant/projeto ou em um secret manager, emitir apenas estado mascarado e registrar health/custo no ledger existente. JSON local pode servir para desenvolvimento, não para a separação de tenants em produção.

O serviço `backend/app/services/transcribe.py` usa Groq com Whisper como caminho preferencial e um endpoint Whisper/OpenAI-compatible como fallback. Ele normaliza segmentos, timestamps, idioma e respostas SRT/JSON; para mídia longa, fatiar em blocos de 10 minutos e deslocar offsets. Esse padrão se encaixa diretamente em mensagens de voz do WhatsApp, desde que o Mago imponha limite de tamanho/duração, retenção, consentimento e armazenamento isolado por tenant.

O serviço `backend/app/services/jobs.py` possui um modelo de execução resiliente: estados terminais, heartbeat, owner PID/host, reconciliação de órfãos no boot, eventos estruturados, trilha append-only, cancelamento cooperativo, persistência com throttle e shutdown limpo. O Mago já possui workers, outbox, tracing e controles de resiliência; portanto a recomendação é portar os **estados e contratos**, não a implementação baseada em arquivos e threads daemon.

## Mapa de integração no Mago Bot

| Capacidade do gentle-aid | Adaptação no Mago | Prioridade | Impacto |
|---|---|---:|---|
| Catálogo declarativo de providers | Registry de modelos/serviços server-side com health, timeout, circuit breaker, custo e fallback | Alta | Reduz segredo espalhado e torna IA operável por tenant |
| Testes de credencial por método | Endpoint operacional mascarado com probes seguros e remediação | Alta | Diminui diagnóstico manual e melhora suporte |
| Groq Whisper + fallback Whisper | Worker de áudio WhatsApp com `media.received → transcription.completed/failed` | Alta | Habilita resposta a áudio e indexação de voz |
| Segmentos/timestamps/SRT | Contrato normalizado de transcript e artefatos por conversation/event | Média | Permite auditoria e busca temporal |
| Heartbeat/orphan healing | Estados do job no PostgreSQL/Redis, lease e retry com idempotência | Alta | Evita jobs presos e tela de “processando” eterna |
| Histórico de jobs | UI de job/trace no portal ou Operations Console | Média | Melhora transparência para cliente e suporte |
| Gemini/OpenRouter para visão/recap | Adapter de IA multimodal sobre mensagens e mídias recebidas | Média | Resumo, intenção e análise de anexos |
| Tavily/Exa/Firecrawl/Jina | Ferramentas opcionais de knowledge retrieval com allowlist, cache e citação | Média | RAG com fontes, mas aumenta latência e risco de dados |
| Voice cloning, TikTok, YouTube, esterilização e bypass | Não portar para o core WhatsApp | Baixa | Contexto diferente, superfície de risco e manutenção desnecessária |
| Auto-update e mirror aaPanel | Não copiar sem revisão | Baixa | Deploy do Mago já tem modelo próprio; scripts podem sobrescrever produção |

## Priorização das APIs citadas

A integração de todas as chaves não equivale a evolução de produto. A primeira onda recomendada é pequena:

| Onda | Serviços | Função no Mago | Decisão |
|---|---|---|---|
| 1 — núcleo | **Groq + Whisper compatível**, **Gemini ou OpenRouter**, **Langfuse** | Áudio, LLM principal/fallback e tracing/evals | Integrar primeiro, com limites e mascaramento |
| 2 — conhecimento | **Jina ou Firecrawl**, mais **Tavily ou Exa** | Ingestão, extração e pesquisa para RAG por tenant | Escolher um extrator e um buscador, não todos |
| 3 — especialização | **Cohere Rerank**, **Mistral** ou **DeepSeek** | Rerank, classificação, resumo e alternativa de modelo | Ativar por capability/tenant após medir qualidade |
| 4 — infraestrutura | **Cloudflare Workers AI**, **Hugging Face**, **SiliconFlow** | Inferência edge/open source ou plano de contingência | Só quando houver volume, requisito regional ou custo comprovado |
| fora do núcleo | **LamaTok** | Social listening/TikTok | Não entra no produto WhatsApp principal; eventual módulo separado |

## Três arquiteturas possíveis

### A. Direta e controlável

O Mago chama Groq para transcrição, Gemini para multimodalidade e Langfuse para tracing. É o caminho recomendado para o primeiro piloto porque reduz hops, pontos de falha e ambiguidade de custo. OpenRouter pode ser adicionado somente como fallback explícito.

### B. Gateway multi-provider

O Mago usa OpenRouter para roteamento/fallback, com Groq/Gemini/Mistral/DeepSeek como opções. Entrega flexibilidade e continuidade, mas adiciona uma dependência intermediária, possível latência e políticas de dados do provider final. O Mago deve registrar o provider efetivo em cada trace e ter fallback local quando o gateway estiver indisponível.

### C. Edge e open source

Cloudflare Workers AI ou Hugging Face/SiliconFlow atendem workloads de embeddings, classificação e transcrição com modelos abertos. É interessante para volume e requisitos de custo/latência, mas adiciona lock-in, observabilidade distribuída e maior trabalho de conformidade. Não é o primeiro passo.

## Estimativa de maturidade

As notas abaixo são uma estimativa interna de produto, não uma métrica de mercado. Elas medem capacidade demonstrada, não quantidade de chaves cadastradas.

| Dimensão | Hoje | Depois da onda 1 | Depois das ondas 1–3 |
|---|---:|---:|---:|
| Fundação control plane/API | 7/10 | 7,5/10 | 8/10 |
| Inteligência de conversas | 2/10 | 5/10 | 7/10 |
| Experiência de desenvolvedor | 5/10 | 6/10 | 7/10 |
| Operação/observabilidade de IA | 3/10 | 6/10 | 8/10 |
| Produto vendável em piloto assistido | 6/10 | 7,5/10 | 8/10 |
| SaaS self-service equivalente a Twilio | 3,5/10 | 4,5/10 | 6/10 |

A última linha não sobe apenas com IA. Para atingir nível Twilio/360dialog ainda são necessários Embedded Signup da Meta, provisionamento WABA/número, templates e qualidade, billing/usage, SDKs, documentação pública, suporte, antiabuso, DPA/LGPD, SLA e onboarding self-service. A Twilio organiza sua oferta em Messaging, Email, Voice, Conversations, Flex/Studio, identidade e dados, e a documentação de Conversations separa estado, inteligência, memória, conhecimento e handoff; esse é o padrão de produto a perseguir, não uma lista de providers.[1] [2] [3]

## Próximo gate recomendado

Implementar no Mago Bot uma **AI Gateway v1** com quatro contratos: `ModelProvider`, `TranscriptionProvider`, `RetrievalProvider` e `ObservabilitySink`. A primeira entrega deve incluir registry de capabilities, credenciais server-side, timeout/retry/circuit breaker, budget por tenant, trace com modelo/provider/prompt/latência/custo, job assíncrono de áudio e evento de handoff. Só depois de esse contrato passar no canário devem ser conectados providers adicionais.

## Conclusão

O gentle-aid tem lógica útil e acelera a evolução, sobretudo em áudio e jobs resilientes. O caminho profissional é **extrair padrões e reimplementar no domínio do Mago**, sem fazer merge de branches, sem importar `__pycache__`, sem copiar filesystem local e sem ligar todas as APIs ao mesmo tempo. A integração da onda 1 transforma o Mago em uma plataforma inteligente de WhatsApp apta a piloto; a transformação em produto SaaS equivalente aos líderes ainda depende principalmente de onboarding oficial Meta, confiabilidade comercial e experiência de desenvolvedor.

## Referências

[1]: https://www.twilio.com/en-us "Twilio — Conversational AI and APIs"
[2]: https://www.twilio.com/docs/whatsapp/api "Twilio — WhatsApp Business Platform with Twilio"
[3]: https://www.twilio.com/docs/conversations "Twilio — Conversations"
[4]: https://openrouter.ai/docs/guides/routing/provider-selection "OpenRouter — Provider Routing"
[5]: https://developers.cloudflare.com/workers-ai/ "Cloudflare — Workers AI"
[6]: https://langfuse.com/docs "Langfuse — Documentation"
[7]: https://api-docs.deepseek.com/ "DeepSeek — API Documentation"
[8]: https://ai.google.dev/gemini-api/docs "Google — Gemini API Documentation"
[9]: https://console.groq.com/docs "Groq — API Documentation"
[10]: https://docs.mistral.ai/ "Mistral — Documentation"
[11]: https://docs.cohere.com/ "Cohere — Documentation"
[12]: https://docs.tavily.com/ "Tavily — Documentation"
[13]: https://jina.ai/reader/ "Jina — Reader"
[14]: https://docs.firecrawl.dev/ "Firecrawl — Documentation"
[15]: https://exa.ai/docs/reference/search-api-guide "Exa — Search API Guide"
[16]: https://huggingface.co/docs/api-inference/index "Hugging Face — Inference API"
[17]: https://docs.siliconflow.com/en/userguide/introduction "SiliconFlow — Documentation"
[18]: https://developers.openai.com/api/docs/guides/speech-to-text "OpenAI — Speech to Text"
