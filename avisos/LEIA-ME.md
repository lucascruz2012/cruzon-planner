# Avisos para o administrador

A rotina `.github/workflows/avisos-admin.yml` roda **a cada 15 minutos** e te avisa por **e-mail** (e, se quiser, também pelo **WhatsApp**) quando:

- alguém **se cadastra** em qualquer app CruzOn (mostra o app e **quem indicou**);
- um **período de teste termina**;
- um **plano mensal ou anual vence**;
- chega um **recado**, inclusive o aviso automático **"Pagamento por Pix informado"**, quando a pessoa toca em *Já paguei*.

Sem a configuração abaixo a rotina roda e termina sem fazer nada.

## Configuração (uma vez, uns 10 minutos)

### 1. Chave do Supabase
No Supabase do Planner: **Project Settings › API Keys** (ou **API**) › copie a chave **service_role** (ou *secret*). Ela dá acesso total ao banco: **nunca** cole no código nem envie a ninguém, só no segredo do GitHub do passo 3.

### 2. Senha de app do Gmail
1. Entre em **myaccount.google.com › Segurança** e confirme que a **Verificação em duas etapas** está ligada.
2. Abra **myaccount.google.com/apppasswords**, dê o nome **Avisos CruzOn** e clique em **Criar**.
3. Copie a senha de 16 letras que aparece.

### 3. Segredos no GitHub
No repositório **cruzon-planner**: **Settings › Secrets and variables › Actions › New repository secret**. Crie um por vez:

| Nome | Valor |
|---|---|
| `SUPABASE_SERVICE_KEY` | a chave do passo 1 |
| `GMAIL_USER` | o seu Gmail (quem envia) |
| `GMAIL_APP_PASSWORD` | a senha de 16 letras do passo 2 |
| `AVISO_EMAIL` | o e-mail que recebe os avisos (pode ser o mesmo) |

### 4. (Opcional) Receber também no WhatsApp
Usa o serviço gratuito **CallMeBot**:
1. Salve nos contatos do celular o número indicado em **callmebot.com › WhatsApp** (o número muda de vez em quando; confira lá).
2. Mande para ele, pelo WhatsApp: `I allow callmebot to send me messages`.
3. Ele responde com a sua **apikey**.
4. Crie mais dois segredos: `CALLMEBOT_PHONE` (seu número com 55 e DDD, só dígitos) e `CALLMEBOT_APIKEY`.

### 5. Testar
Em **Actions › Avisos para o administrador › Run workflow**. Se houver novidade nos últimos 20 minutos, o aviso chega. O log mostra só quantidades (o repositório é público), nunca nomes ou e-mails.

## Bom saber
- O GitHub pausa rotinas agendadas de repositórios sem nenhuma alteração por 60 dias. Se os avisos pararem, abra **Actions** e clique em **Enable workflow**.
- Se o envio falhar, a execução fica vermelha e a próxima tenta de novo a mesma janela de tempo, então nada se perde.
