# MFA do owner com Google Authenticator

## O que está sendo usado

O Mago Bot usa **TOTP**, o padrão de códigos temporários baseado em tempo. O app oficial [Google Authenticator](https://support.google.com/accounts/answer/1066447) é compatível com esse padrão e não exige Google Cloud, API paga ou integração de login do Google.

Isso é diferente de **Entrar com Google** e de Google Workspace 2-Step Verification. O Mago Bot não depende de uma conta Google para gerar o código. O aplicativo Google Authenticator apenas guarda o segredo TOTP localmente ou na sincronização escolhida pelo usuário e gera um código de seis dígitos a cada período de 30 segundos.

## Fluxo seguro na Operations Console

1. Entre em `https://evo-api.mago-bot.com/` com a conta owner.
2. Abra **Proprietário** e confirme que o status está `MFA Pendente`.
3. Clique em **Ativar Google Authenticator do owner** e depois em **Gerar setup MFA**.
4. Cadastre o QR Code ou a URI exibida diretamente no Google Authenticator. Se o mesmo dispositivo não permitir escanear a tela, use a opção de inserir uma chave de configuração manualmente.
5. Armazene os códigos de recuperação em um gerenciador de senhas confiável. Eles aparecem uma única vez.
6. Digite o código TOTP atual no campo da Console e clique em **Confirmar MFA**.
7. Atualize a tela e confirme **Google Authenticator / MFA — ativo**.

O Mago Bot grava apenas o segredo TOTP cifrado server-side, os hashes dos códigos de recuperação e o contador anti-replay necessário. A aplicação não grava QR em log, não mostra o segredo em OpenAPI e não envia o código para terceiros.

## Regras de segurança

Nunca envie pelo chat o QR Code, a URI `otpauth://`, a chave manual, um código TOTP, códigos de recuperação, senha ou token. O suporte legítimo nunca precisa desses valores.

O código TOTP expira rapidamente e depende do relógio do dispositivo. Mantenha data e hora automáticas no celular. O Mago aceita uma pequena janela de tolerância para compensar diferença normal de relógio e rejeita o mesmo contador duas vezes.

Se o celular for perdido, use um código de recuperação ainda não consumido, entre na Console e desative/reconfigure o MFA. Se não houver recuperação, será necessário seguir o procedimento administrativo de recuperação de conta; não tente editar o banco ou o `.env`.

## Gate do produto

O MFA do owner é obrigatório para criar tenants/projetos e iniciar o laboratório Evolution. A conta owner continua tendo todos os privilégios customer-scoped e poderes adicionais, mas não existe wildcard sem autenticação forte. Depois de o MFA ficar ativo, o próximo fluxo é provisionar o tenant/projeto de laboratório e conectar o número exclusivo por QR/pairing.

## Parâmetros de compatibilidade

| Parâmetro | Valor |
|---|---|
| Padrão | TOTP |
| Algoritmo | HMAC-SHA1 |
| Dígitos | 6 |
| Período | 30 segundos |
| URI | `otpauth://totp/...` |
| Aplicativos compatíveis | Google Authenticator e autenticadores TOTP equivalentes |

O teste local baseado no vetor público RFC 6238 confirmou a geração e verificação do código, além da URI `otpauth` com issuer `Mago Bot`, algoritmo SHA1, seis dígitos e período de 30 segundos.
