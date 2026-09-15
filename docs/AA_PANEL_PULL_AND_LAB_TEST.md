# Pull e teste de laboratório no aaPanel

Este procedimento é para a **API Mago Bot** (`app.mago-bot.com` / `evo-api.mago-bot.com`). Não aplicar no CRM `mago-bot.com` e não usar o número de produção.

## Escopo

O branch contém a base do control plane, superfície M2M, canal customer, QR SVG, Evolution adapter, workers, migrations e verificadores. O objetivo deste procedimento é atualizar o código com backup e validar o canal de laboratório. Ele não inclui chaves, QR, cookies, TOTP, HMAC secret, dumps ou o arquivo produtivo `evolution-provider.env`.

## Antes do pull

Faça um snapshot do diretório e confirme que o destino é `/opt/mago-platform` ou o caminho real configurado para a API Mago Bot. Não execute `git reset --hard` em produção. Preserve o arquivo de ambiente produtivo, o Compose efetivo, os volumes e o banco. O CRM deve permanecer fora desta operação.

## Pull seguro

No servidor, com acesso root e após conferir o diretório:

```bash
cd /opt/mago-platform
stamp=$(date -u +%Y%m%dT%H%M%SZ)
tar -czf "/var/backups/mago-platform/pre-pull-$stamp.tgz" service docker-compose.production.yml evolution-provider.env 2>/dev/null || true
git fetch origin audit/estado-real-producao-2026-09-15
git diff --stat HEAD origin/audit/estado-real-producao-2026-09-15
```

Aplique o conteúdo somente depois de revisar a diferença. O arquivo `service/deploy/service.env.example` é um exemplo; não substitua o ambiente produtivo por ele. Nunca copie `evolution-provider.env` para o Git.

## Migrations

As migrations são forward-only. Antes de aplicar uma migration, faça dump verificável do banco da plataforma e confira a versão já aplicada. Não reinicie PostgreSQL, Redis ou Evolution sem necessidade. Se o schema já estiver na versão correspondente, não reaplique manualmente.

```bash
cd /opt/mago-platform/service
python3 -m compileall -q app
node --check app/assets/platform-app.js
node --check app/assets/ops-app.js
```

## Rebuild restrito

Recrie somente o serviço da API quando a alteração for de aplicação/UI. Workers e Evolution só devem ser recriados se os arquivos correspondentes mudaram e o canário passou. Não reinicie o CRM, os bancos ou Redis durante o primeiro teste.

```bash
cd /opt/mago-platform
/usr/bin/docker-compose -f docker-compose.production.yml up -d --build licensing-app
```

Valide:

```bash
curl -fsS https://app.mago-bot.com/health/live
curl -fsS https://app.mago-bot.com/health/ready
curl -fsSI https://app.mago-bot.com/docs
curl -fsSI https://evo-api.mago-bot.com/ops
```

## Teste do canal de laboratório

Use a API key de laboratório somente em variável local ou gerenciador seguro. Nunca cole a chave no chat e nunca a coloque em comando salvo, histórico, HTML ou log. Use um `X-Idempotency-Key` novo para cada mutation. Não crie outro canal se o canal existente aparecer na listagem.

O teste funcional é:

1. Confirmar exatamente um canal de laboratório no projeto correto.
2. Consultar o status sem gerar QR repetidamente.
3. Solicitar um QR novo uma única vez.
4. Escanear imediatamente no WhatsApp exclusivo de laboratório.
5. Consultar status até `connected`/`open` confirmado e reconciliado no control plane.
6. Verificar webhook de conexão em receptor HTTPS controlado.
7. Só depois testar mensagem para destinatário com opt-in explícito.

O conteúdo do QR é efêmero e não deve ser enviado por chat, registrado em log ou incluído em relatório.

## Rollback

Se health, readiness, OpenAPI, autenticação, isolamento ou logs falharem, pare o rollout, não faça novas mutations e restaure o snapshot de código/Compose preservando dados. Não faça rollback SQL improvisado. Registre timestamp, commit, gate que falhou e estado dos containers.

## Resultado esperado

O teste só pode ser declarado aprovado quando o provider e o control plane concordarem no estado do canal, o QR for escaneado com sucesso, o webhook assinado for validado e não houver duplicidade em retries. Conexão visual no WhatsApp isoladamente não é prova suficiente de E2E.
