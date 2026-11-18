-- CruzOn: preços públicos para a página "Conheça" (atualizam sozinhos quando você muda em Ajustes › Planos e cobrança).
-- Entrega só os preços de cada app e os dias de teste; o resto da configuração (Pix, WhatsApp, e-mails) continua protegido.
-- Rode uma vez no Supabase: SQL Editor -> New query -> colar -> Run. Pode rodar de novo sem problema.
create or replace function public.cruzon_precos_publicos()
returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'teste_ativo', coalesce(teste_ativo, false),
    'teste_dias',  teste_dias,
    'planner', json_build_object('mensal', preco_mensal,         'anual', preco_anual),
    'finance', json_build_object('mensal', preco_mensal_finance, 'anual', preco_anual_finance),
    'invest',  json_build_object('mensal', preco_mensal_invest,  'anual', preco_anual_invest))
  from public.config_app where id = 1;
$$;
revoke all on function public.cruzon_precos_publicos() from public;
grant execute on function public.cruzon_precos_publicos() to anon, authenticated;
