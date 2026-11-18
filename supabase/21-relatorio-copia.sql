-- CruzInvest: o relatório agendado por e-mail (segunda, quarta e sexta, e a análise mensal) manda cópia
-- para os mesmos endereços de "E-mail em cópia nos avisos" (Planner › Ajustes › Planos e cobrança).
-- O relatório lê esse campo por esta função, que só responde a quem informar a chave do relatório.
-- Rode uma vez no Supabase: painel do projeto -> SQL Editor -> New query -> colar -> Run.
-- Antes, troque COLE_A_CHAVE pela chave que o assistente passou na conversa (não grave a chave no repositório).
-- Precisa do 17-aviso-copia.sql. Pode rodar de novo; para trocar a chave, rode com uma chave nova.
alter table public.config_app add column if not exists aviso_cc text;
alter table public.config_app add column if not exists relatorio_chave text;
update public.config_app set relatorio_chave = 'COLE_A_CHAVE' where id = 1;

create or replace function public.relatorio_copia(chave text)
returns text language sql stable security definer set search_path = public as $$
  select coalesce(aviso_cc, '') from public.config_app
  where id = 1 and relatorio_chave is not null and length(relatorio_chave) >= 24
    and relatorio_chave <> 'COLE_A_CHAVE' and relatorio_chave = chave;
$$;
revoke all on function public.relatorio_copia(text) from public;
grant execute on function public.relatorio_copia(text) to anon, authenticated;
