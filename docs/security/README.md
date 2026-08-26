# Chave SSH exclusiva do repositório

Foi criada uma chave Ed25519 exclusiva para a integração do repositório com o Manus.

- Comentário: `mago-bot-manus-repository-2026`
- Fingerprint: `SHA256:yUhI9zkycKnfnHdqi9PuHEz8hrMa2aEzjV78XPvcJ/U`
- Chave pública: `mago_manus_repo_ed25519.pub`

A chave privada não está neste repositório. Ela fica na máquina de operação em:

`/root/.ssh/mago_manus_repo_ed25519`

Status: registrada no GitHub como Deploy Key `Mago Bot Manus - read only`, com acesso somente leitura às branches do repositório.

Se futuramente o Manus precisar fazer push, criar outra credencial com permissão de escrita e aprovação explícita. Não transformar esta chave em chave de escrita. Nunca publicar a chave privada em issue, commit, variável pública ou arquivo do projeto.
