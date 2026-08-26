# Chave SSH exclusiva do repositório

Foi criada uma chave Ed25519 exclusiva para a integração do repositório com o Manus.

- Comentário: `mago-bot-manus-repository-2026`
- Fingerprint: `SHA256:yUhI9zkycKnfnHdqi9PuHEz8hrMa2aEzjV78XPvcJ/U`
- Chave pública: `mago_manus_repo_ed25519.pub`

A chave privada não está neste repositório. Ela fica na máquina de operação em:

`/root/.ssh/mago_manus_repo_ed25519`

Status: registrada no GitHub como Deploy Key `Mago Bot Manus - read write`, com acesso de leitura e escrita às branches do repositório.

Essa chave permite ao Manus clonar, auditar, criar branches, editar código e enviar commits. Ela não concede acesso ao painel aaPanel, ao SSH do servidor ou aos segredos de produção. Nunca publicar a chave privada em issue, commit, variável pública ou arquivo do projeto.
