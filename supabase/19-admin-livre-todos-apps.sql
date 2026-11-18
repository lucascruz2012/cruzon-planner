-- CruzOn: administrador sempre liberado (gratuito) no Finance e no CruzInvest, como já é no Planner.
-- Rode uma vez no Supabase: SQL Editor -> New query -> colar -> Run. Pode rodar de novo sem problema.

-- 1) quem já é administrador hoje fica gratuito nos dois apps
insert into public.app_acessos (user_id, app, isento, bloqueado)
select p.id, a.app, true, false
from public.perfis p cross join (values ('finance'), ('invest')) as a(app)
where p.papel = 'admin'
on conflict (user_id, app) do update set isento = true, bloqueado = false;

-- 2) daqui para frente: ao abrir o Finance ou o CruzInvest, administrador já entra gratuito
create or replace function public.app_acesso(p_app text)
returns public.app_acessos language plpgsql security definer set search_path = public as $$
declare r public.app_acessos; t boolean; d integer;
begin
  if auth.uid() is null then raise exception 'sem login'; end if;
  if p_app not in ('finance','invest') then raise exception 'app inválido'; end if;
  if public.cruzon_eh_admin() then
    insert into public.app_acessos (user_id, app, isento, bloqueado) values (auth.uid(), p_app, true, false)
    on conflict (user_id, app) do update set isento = true, bloqueado = false;
  end if;
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
