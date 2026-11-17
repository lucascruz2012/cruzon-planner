# CruzOn Finance

Gestão financeira pessoal: receitas, despesas, cartões e faturas, carteiras, orçamentos, metas e relatórios em PDF e Excel. **Seu dinheiro sempre ligado.**

**Endereço:** `https://lucascruz2012.github.io/cruzon-planner/finance/`

## Conta e sincronização

O CruzOn Finance usa a **mesma conta do CruzOn Planner e do CruzInvest** (mesmo e-mail e senha, mesmo Supabase). Os dados ficam iguais em todos os aparelhos: o que muda em um aparece nos outros em poucos segundos.

Configuração (uma vez): rode o arquivo [`supabase.sql`](supabase.sql) no **SQL Editor** do Supabase do Planner. Ele cria a tabela `finance_cofres`, separada das tabelas do Planner e do CruzInvest, com acesso só do próprio dono. Enquanto a tabela não existir, o app funciona só no aparelho.

Se a senha for trocada pelo Planner ("Esqueci a senha"), o Finance pede a senha anterior uma vez para reabrir os dados, porque eles são criptografados com a senha.

Quem não quiser usar a internet pode escolher **Usar só neste aparelho** na tela de entrada.

## Segurança

- Os dados são **criptografados no aparelho antes de ir para a nuvem** (AES-256-GCM; chave derivada da senha por PBKDF2-SHA-256 com 310 mil iterações). A senha e a chave nunca são gravadas.
- O Supabase guarda só o texto cifrado; sem a senha, ninguém lê os lançamentos, nem o administrador.
- O app se bloqueia sozinho após 20 minutos sem uso.

## Arquivos

- `index.html`: o app inteiro.
- `manual.pdf` e `guia.pdf`: Manual do Usuário e Guia Rápido.
- `manifest.webmanifest`, `sw.js` e ícones: instalação no celular e uso sem internet.
- `supabase.sql`: tabela da sincronização.

O código-fonte e as ferramentas de teste ficam no projeto do CruzOn Finance; esta pasta recebe só o resultado do `npm run site`.
