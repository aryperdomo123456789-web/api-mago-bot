# Estado real do deploy API Mago Bot — 15/09/2026

## Escopo

Este registro cobre exclusivamente:

- https://app.mago-bot.com/
- https://evo-api.mago-bot.com/
- servidor `69.197.184.45`
- repositório https://github.com/aryperdomo123456789-web/api-mago-bot

## Resultado

O servidor não possui `.git` em `/opt/mago-platform`. Portanto, o deploy não é rastreável diretamente por um commit local.

A comparação por SHA-256 mostrou que o código implantado se aproxima da branch `feat/operations-console-admin-migration`, commit:

`2cb78b346729de0ef1282bf9281b7a28d4c19a04`

A branch contém 140 arquivos sob `service/`. O servidor contém 138 arquivos equivalentes:

- 128 arquivos coincidem exatamente;
- 10 arquivos têm conteúdo diferente;
- 2 arquivos não estão no servidor.

Arquivos ausentes no servidor:

- `tests/test_m2m.py`
- `tests/test_qr_code.py`

Arquivos com conteúdo diferente:

- `README.md`
- `README_OPERATIONS_CONSOLE.md`
- `README_PLATFORM_V1.md`
- `app/assets/ops-app.js`
- `app/assets/public-home.html`
- `app/evolution_health_worker.py`
- `app/platform_models.py`
- `app/providers/evolution_management.py`
- `app/routes/admin.py`
- `app/routes/email_ops.py`
- `app/routes/ops_ui.py`

## Conclusão

As duas superfícies estão operacionais, mas o servidor não está perfeitamente sincronizado com o GitHub. A branch publicada por este documento registra o estado conhecido, as divergências e os documentos de arquitetura.

Não executar `git pull`, `reset` ou sobrescrever produção sem preservar um snapshot e revisar as divergências.

## Documentos relacionados

- [Auditoria de prontidão do produto API Mago Bot v1](AUDITORIA-PRODUTO-API-MAGO-BOT-V1.md)
- [Receita de implementação da camada de e-mail](RECEITA-IMPLEMENTACAO-CAMADA-EMAIL-MAGO-BOT.md)

