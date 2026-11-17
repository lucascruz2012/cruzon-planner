-- CruzOn Planner: Pix na tela de assinatura.
-- Rode uma vez no Supabase: painel do projeto -> SQL Editor -> New query -> colar -> Run.
-- Acrescenta à configuração do app a chave Pix, o nome e a cidade de quem recebe.
-- Não apaga nem altera nada que já existe.
alter table public.config_app add column if not exists pix_chave  text;
alter table public.config_app add column if not exists pix_nome   text;
alter table public.config_app add column if not exists pix_cidade text;
