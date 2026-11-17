-- CruzOn: acesso, teste e assinatura separados por app (CruzOn Finance e CruzInvest).
-- O CruzOn Planner continua usando os campos que já existem em "perfis" (plano, acesso_ate, isento, ativo).
-- Rode uma vez no Supabase: painel do projeto -> SQL Editor -> New query -> colar -> Run.
-- Não apaga nem altera nenhum dado que já existe. Pode rodar de novo sem problema.

-- 1) Preço de cada app (o Planner continua com preco_mensal e preco_anual)
alter table public.config_app add column if not exists preco_mensal_finance numeric;
alter table public.config_app add column if not exists preco_anual_finance  numeric;
alter table public.config_app add column if not exists preco_mensal_invest  numeric;
alter table public.config_app add column if not exists preco_anual_invest   numeric;

-- 2) Acesso de cada pessoa a cada app
create table if not exists public.app_acessos (
  user_id    uuid        not null references auth.users(id) on delete cascade,
  app        text        not null check (app in ('finance','invest')),
  plano      text,                         -- teste | mensal | anual | null (sem prazo)
  acesso_ate timestamptz,                  -- null = sem prazo
  isento     boolean     not null default false,  -- gratuito
  bloqueado  boolean     not null default false,
  criado_em  timestamptz not null default now(),
  primary key (user_id, app)
);
alter table public.app_acessos enable row level security;

-- quem é administrador (usado nas regras abaixo)
create or replace function public.cruzon_eh_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists(select 1 from public.perfis where id = auth.uid() and papel = 'admin');
$$;

drop policy if exists "acessos: ve o seu ou admin" on public.app_acessos;
drop policy if exists "acessos: admin cria"        on public.app_acessos;
drop policy if exists "acessos: admin altera"      on public.app_acessos;
drop policy if exists "acessos: admin apaga"       on public.app_acessos;
create policy "acessos: ve o seu ou admin" on public.app_acessos for select using (auth.uid() = user_id or public.cruzon_eh_admin());
create policy "acessos: admin cria"        on public.app_acessos for insert with check (public.cruzon_eh_admin());
create policy "acessos: admin altera"      on public.app_acessos for update using (public.cruzon_eh_admin()) with check (public.cruzon_eh_admin());
create policy "acessos: admin apaga"       on public.app_acessos for delete using (public.cruzon_eh_admin());

-- 3) O app pergunta o acesso da pessoa. Na primeira vez, o próprio banco cria o período de teste
--    (com os dias definidos em Ajustes), assim ninguém consegue aumentar o prazo por conta própria.
create or replace function public.app_acesso(p_app text)
returns public.app_acessos language plpgsql security definer set search_path = public as $$
declare r public.app_acessos; t boolean; d integer;
begin
  if auth.uid() is null then raise exception 'sem login'; end if;
  if p_app not in ('finance','invest') then raise exception 'app inválido'; end if;
  select * into r from public.app_acessos where user_id = auth.uid() and app = p_app;
  if found then return r; end if;
  select coalesce(teste_ativo, false), coalesce(teste_dias, 7) into t, d from public.config_app where id = 1;
  insert into public.app_acessos (user_id, app, plano, acesso_ate)
  values (auth.uid(), p_app,
          case when t then 'teste' end,
          case when t then now() + make_interval(days => d) end)
  on conflict (user_id, app) do nothing;
  select * into r from public.app_acessos where user_id = auth.uid() and app = p_app;
  return r;
end $$;
revoke all on function public.app_acesso(text) from public;
grant execute on function public.app_acesso(text) to authenticated;

-- 4) Dados da tela de assinatura de cada app (preços, Pix e WhatsApp), sem expor o resto da configuração
create or replace function public.app_planos(p_app text)
returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'preco_mensal', case p_app when 'finance' then preco_mensal_finance when 'invest' then preco_mensal_invest else preco_mensal end,
    'preco_anual',  case p_app when 'finance' then preco_anual_finance  when 'invest' then preco_anual_invest  else preco_anual  end,
    'teste_dias', teste_dias, 'whatsapp', whatsapp, 'recado', recado,
    'pix_chave', pix_chave, 'pix_nome', pix_nome, 'pix_cidade', pix_cidade)
  from public.config_app where id = 1 and auth.uid() is not null;
$$;
revoke all on function public.app_planos(text) from public;
grant execute on function public.app_planos(text) to authenticated;
