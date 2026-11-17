-- CruzOn: e-mail em cópia nos avisos do vigia (configurado em Ajustes › Planos e cobrança).
-- Rode uma vez no Supabase: painel do projeto -> SQL Editor -> New query -> colar -> Run. Pode rodar de novo sem problema.
alter table public.config_app add column if not exists aviso_cc text;
