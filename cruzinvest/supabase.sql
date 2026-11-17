-- CruzInvest: tabela da carteira sincronizada entre aparelhos.
-- Rode uma vez no Supabase do CruzOn Planner: painel do projeto -> SQL Editor -> New query -> colar -> Run.
-- A carteira chega aqui já criptografada pelo app (AES-256-GCM, chave derivada da senha do usuário):
-- o banco guarda só texto cifrado. Não mexe em nenhuma tabela do CruzOn Planner.

create table if not exists public.invest_cofres (
  user_id       uuid primary key references auth.users(id) on delete cascade,
  salt          text        not null,
  iter          integer     not null,
  box           jsonb       not null,
  atualizado_em timestamptz not null default now()
);

alter table public.invest_cofres enable row level security;

drop policy if exists "invest: dono le"     on public.invest_cofres;
drop policy if exists "invest: dono cria"   on public.invest_cofres;
drop policy if exists "invest: dono altera" on public.invest_cofres;
drop policy if exists "invest: dono apaga"  on public.invest_cofres;

create policy "invest: dono le"     on public.invest_cofres for select using (auth.uid() = user_id);
create policy "invest: dono cria"   on public.invest_cofres for insert with check (auth.uid() = user_id);
create policy "invest: dono altera" on public.invest_cofres for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "invest: dono apaga"  on public.invest_cofres for delete using (auth.uid() = user_id);
