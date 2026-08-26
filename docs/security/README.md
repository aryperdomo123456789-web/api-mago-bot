# Chave SSH exclusiva do repositório

Foi criada uma chave Ed25519 exclusiva para a integração do repositório com o Manus.

- Comentário: `mago-bot-manus-repository-2026`
- Fingerprint: `SHA256:yUhI9zkycKnfnHdqi9PuHEz8hrMa2aEzjV78XPvcJ/U`
- Chave pública: `mago_manus_repo_ed25519.pub`

A chave privada não está neste repositório. Ela fica na máquina de operação em:

`/root/.ssh/mago_manus_repo_ed25519`

Para usar como Deploy Key no GitHub, adicionar o conteúdo da chave pública nas configurações do repositório e ativar escrita somente se o Manus realmente precisar fazer push. Para leitura, manter a chave sem permissão de escrita. Nunca publicar a chave privada em issue, commit, variável pública ou arquivo do projeto.
