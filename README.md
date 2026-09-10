# CRUZON Planner RH

Aplicativo de planejamento semanal de atividades de RH/DP — arquivo único, sem instalação e sem servidor.

**Acesso:** https://SEU-USUARIO.github.io/cruzon-planner/
*(troque `SEU-USUARIO` pelo seu usuário do GitHub depois de ativar o Pages)*

---

## Como publicar (primeira vez)

1. No GitHub, clique em **New repository**. Nome sugerido: `cruzon-planner`. Deixe **Public** e clique em **Create repository**.
2. Na tela seguinte, clique em **uploading an existing file** e arraste o `index.html` (e este `README.md`, se quiser). Clique em **Commit changes**.
3. Vá em **Settings → Pages**. Em *Source*, escolha **Deploy from a branch**; em *Branch*, selecione **main** e a pasta **/ (root)**. Clique em **Save**.
4. Aguarde de 1 a 2 minutos e abra o endereço que o GitHub mostrar no topo da página de Pages.

## Como atualizar para uma versão nova

1. No repositório: **Add file → Upload files**.
2. Arraste o `index.html` novo (mesmo nome) e confirme em **Commit changes** — o GitHub substitui o arquivo.
3. Em cerca de um minuto o site está no ar. Se o navegador insistir na versão antiga, atualize com **Ctrl + F5**.

> Trocar o arquivo **não apaga as atividades**: elas ficam gravadas no navegador de cada pessoa, não dentro do arquivo.

## Antes de migrar do arquivo local para o site

Os dados do arquivo aberto por duplo clique (`file://`) **não** aparecem no site, porque o navegador trata os dois como lugares diferentes. Para levar tudo:

1. No arquivo local: **Ajustes → Exportar backup completo**.
2. Abra o site pela primeira vez, crie o mesmo perfil de administrador e vá em **Ajustes → Restaurar backup**.
3. Selecione o arquivo `.json` exportado no passo 1.

## O que é público e o que não é

- **Público:** o código do aplicativo, o logotipo e a arte da tela de login — qualquer pessoa com o endereço vê a tela de login.
- **Não público:** as atividades, os perfis e as senhas. Nada disso vai para o GitHub — fica no navegador de cada computador, com o cofre criptografado em AES-256.
- Cada computador/navegador tem a sua própria base. Para levar dados de um para o outro, use exportar/restaurar backup.

## Estrutura

- `index.html` — o aplicativo inteiro (páginas, estilos, scripts, fontes, logotipo e imagens embutidos).
