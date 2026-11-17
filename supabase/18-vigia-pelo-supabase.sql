-- CruzOn: o Supabase aciona o vigia (avisos por e-mail) a cada 10 minutos.
-- Plano B porque o agendamento do GitHub não estava rodando sozinho.
-- Antes: crie no GitHub um token "fine-grained" só para o repositório cruzon-planner,
-- com a permissão "Actions: Read and write" (passo a passo em avisos/LEIA-ME.md).
-- Cole o token no lugar de COLE_AQUI_O_TOKEN no passo 2. Ele fica guardado criptografado no cofre (Vault) do Supabase.
-- Rode no Supabase: SQL Editor -> New query -> colar -> Run. Pode rodar de novo (por exemplo, com um token novo).

-- 1) extensões do Supabase para agendar tarefas e chamar a internet
create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;

-- 2) guarda o token do GitHub no cofre do Supabase (troque o texto entre aspas pelo token)
delete from vault.secrets where name = 'github_vigia_token';
select vault.create_secret('COLE_AQUI_O_TOKEN', 'github_vigia_token');

-- 3) a cada 10 minutos, pede ao GitHub para rodar o vigia
select cron.unschedule('cruzon-vigia') where exists (select 1 from cron.job where jobname = 'cruzon-vigia');
select cron.schedule('cruzon-vigia', '*/10 * * * *', $$
  select net.http_post(
    url     := 'https://api.github.com/repos/lucascruz2012/cruzon-planner/actions/workflows/avisos-admin.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || (select decrypted_secret from vault.decrypted_secrets where name = 'github_vigia_token'),
      'Accept', 'application/vnd.github+json',
      'X-GitHub-Api-Version', '2022-11-28',
      'User-Agent', 'cruzon-vigia'),
    body    := '{"ref":"main","inputs":{"teste":"false"}}'::jsonb);
$$);

-- Para conferir depois de 10 minutos:
--   select status_code, created from net._http_response order by created desc limit 5;
-- 204 = o GitHub aceitou e o vigia rodou. 401 = token errado ou vencido. 403/404 = token sem a permissão "Actions".
