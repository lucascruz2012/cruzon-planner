-- CruzOn Finance: tabela dos dados sincronizados entre aparelhos.
-- Rode uma vez no Supabase do CruzOn Planner: painel do projeto -> SQL Editor -> New query -> colar -> Run.
-- Os dados chegam aqui já criptografados pelo app (AES-256-GCM, chave derivada da senha do usuário):
-- o banco guarda só texto cifrado. Não mexe em nenhuma tabela do CruzOn Planner nem do CruzInvest.

create table if not exists public.finance_cofres (
  user_id       uuid primary key references auth.users(id) on delete cascade,
  salt          text        not null,
  iter          integer     not null,
  box           jsonb       not null,
  atualizado_em timestamptz not null default now()
);

alter table public.finance_cofres enable row level security;

drop policy if exists "finance: dono le"     on public.finance_cofres;
drop policy if exists "finance: dono cria"   on public.finance_cofres;
drop policy if exists "finance: dono altera" on public.finance_cofres;
drop policy if exists "finance: dono apaga"  on public.finance_cofres;

create policy "finance: dono le"     on public.finance_cofres for select using (auth.uid() = user_id);
create policy "finance: dono cria"   on public.finance_cofres for insert with check (auth.uid() = user_id);
create policy "finance: dono altera" on public.finance_cofres for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "finance: dono apaga"  on public.finance_cofres for delete using (auth.uid() = user_id);
