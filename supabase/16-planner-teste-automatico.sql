-- CruzOn Planner: teste automático no primeiro uso (igual ao Finance e ao CruzInvest).
-- Quem se cadastra já entra, sem esperar "Liberar acesso". O teste do Planner começa no primeiro uso do Planner.
-- Quem já estava "Aguardando" continua esperando você liberar. Ninguém que já usa é afetado.
-- Rode uma vez no Supabase: painel do projeto -> SQL Editor -> New query -> colar -> Run. Pode rodar de novo sem problema.

alter table public.perfis add column if not exists planner_teste_pendente boolean not null default false;

-- 1) cadastro novo: já entra liberado, com o teste do Planner marcado para começar no primeiro uso
create or replace function public.cruzon_perfil_novo()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if coalesce(new.papel, 'user') <> 'admin' then
    new.ativo := true;
    new.planner_teste_pendente := true;
  end if;
  return new;
end $$;
drop trigger if exists cruzon_perfil_novo on public.perfis;
create trigger cruzon_perfil_novo before insert on public.perfis
  for each row execute function public.cruzon_perfil_novo();

-- 2) primeiro uso do Planner: o próprio banco começa o teste (com os dias de Ajustes), ninguém aumenta o prazo
create or replace function public.planner_acesso()
returns void language plpgsql security definer set search_path = public as $$
declare t boolean; d integer;
begin
  if auth.uid() is null then return; end if;
  select coalesce(teste_ativo, false), coalesce(teste_dias, 7) into t, d from public.config_app where id = 1;
  update public.perfis set
    planner_teste_pendente = false,
    plano      = case when t and acesso_ate is null and not coalesce(isento, false) then 'teste' else plano end,
    acesso_ate = case when t and acesso_ate is null and not coalesce(isento, false) then now() + make_interval(days => d) else acesso_ate end
  where id = auth.uid() and planner_teste_pendente;
end $$;
revoke all on function public.planner_acesso() from public;
grant execute on function public.planner_acesso() to authenticated;
