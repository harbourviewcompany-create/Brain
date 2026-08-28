-- Reconcile revenue scoring audit tables with the domain's stable text keys.
--
-- Migration 006 modeled revenue_signals.source_id, revenue_signals.money_lane_id,
-- and scored_revenue_opportunities.money_lane_id as UUID foreign keys. The domain
-- carries connector source keys and MoneyLane.lane_id / money_lanes.lane_key strings.
-- Migration 017 already uses text keys for the execution ledger. This migration
-- brings the scoring audit trail onto the same stable-key contract.
--
-- Legacy UUID values are translated only while the corresponding column is still
-- UUID. Once a column is text, replay never interprets a UUID-shaped stable text key
-- as a legacy foreign-key id. Valid legacy nulls remain null.
--
-- Migrations 020-022 FORCE RLS on the tenant-owned scoring tables. The migration
-- runner executes each migration transactionally as the schema migrator/table owner.
-- Temporarily removing FORCE (while leaving RLS enabled) lets that owner translate
-- pre-tenant system rows whose tenant_id is null; FORCE is restored before commit.

do $$
declare
  revenue_source_is_uuid boolean := false;
  revenue_lane_is_uuid boolean := false;
  scored_lane_is_uuid boolean := false;
begin
  select coalesce(c.udt_name = 'uuid', false)
    into revenue_source_is_uuid
  from information_schema.columns c
  where c.table_schema = 'public'
    and c.table_name = 'revenue_signals'
    and c.column_name = 'source_id';

  select coalesce(c.udt_name = 'uuid', false)
    into revenue_lane_is_uuid
  from information_schema.columns c
  where c.table_schema = 'public'
    and c.table_name = 'revenue_signals'
    and c.column_name = 'money_lane_id';

  select coalesce(c.udt_name = 'uuid', false)
    into scored_lane_is_uuid
  from information_schema.columns c
  where c.table_schema = 'public'
    and c.table_name = 'scored_revenue_opportunities'
    and c.column_name = 'money_lane_id';

  if coalesce(revenue_source_is_uuid, false)
     or coalesce(revenue_lane_is_uuid, false)
     or coalesce(scored_lane_is_uuid, false) then
    alter table public.sources no force row level security;
    alter table public.revenue_signals no force row level security;
    alter table public.scored_revenue_opportunities no force row level security;
  end if;

  if coalesce(revenue_source_is_uuid, false) then
    alter table public.revenue_signals
      drop constraint if exists revenue_signals_source_id_fkey;
    alter table public.revenue_signals
      alter column source_id type text using source_id::text;

    update public.revenue_signals rs
    set source_id = s.key
    from public.sources s
    where rs.source_id is not null
      and rs.source_id = s.id::text;
  end if;

  if coalesce(revenue_lane_is_uuid, false) then
    alter table public.revenue_signals
      drop constraint if exists revenue_signals_money_lane_id_fkey;
    alter table public.revenue_signals
      alter column money_lane_id type text using money_lane_id::text;

    update public.revenue_signals rs
    set money_lane_id = ml.lane_key
    from public.money_lanes ml
    where rs.money_lane_id is not null
      and rs.money_lane_id = ml.id::text;
  end if;

  if coalesce(scored_lane_is_uuid, false) then
    alter table public.scored_revenue_opportunities
      drop constraint if exists scored_revenue_opportunities_money_lane_id_fkey;
    alter table public.scored_revenue_opportunities
      alter column money_lane_id type text using money_lane_id::text;

    update public.scored_revenue_opportunities sro
    set money_lane_id = ml.lane_key
    from public.money_lanes ml
    where sro.money_lane_id is not null
      and sro.money_lane_id = ml.id::text;
  end if;

  if coalesce(revenue_source_is_uuid, false)
     or coalesce(revenue_lane_is_uuid, false)
     or coalesce(scored_lane_is_uuid, false) then
    alter table public.sources force row level security;
    alter table public.revenue_signals force row level security;
    alter table public.scored_revenue_opportunities force row level security;
  end if;
end $$;

-- Migration 017 predates tenant ownership. The canonical tenant-aware API now uses
-- PostgresRevenueStore for approval-gated persistence, so its execution ledger must
-- become tenant-owned before that store can be safely exposed to a non-owner runtime
-- login. Legacy/system rows remain tenant_id null and are not destructively backfilled.
alter table public.revenue_execution_actions
  add column if not exists tenant_id uuid references public.tenants(id) on delete restrict;
alter table public.revenue_followups
  add column if not exists tenant_id uuid references public.tenants(id) on delete restrict;
alter table public.revenue_outcome_ledger
  add column if not exists tenant_id uuid references public.tenants(id) on delete restrict;

-- Apply the same tenant default, RLS policies, FORCE boundary, indexes and runtime DML
-- grants that migration 022 applies to tables that already carried tenant_id.
do $$
declare
  t text;
begin
  foreach t in array array[
    'revenue_execution_actions',
    'revenue_followups',
    'revenue_outcome_ledger'
  ] loop
    execute format(
      'alter table public.%I alter column tenant_id set default public.current_brain_tenant_id()',
      t
    );
    execute format('create index if not exists %I on public.%I (tenant_id)', t || '_tenant_id_idx', t);
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);

    execute format('drop policy if exists tenant_isolation_select on public.%I', t);
    execute format(
      'create policy tenant_isolation_select on public.%I for select using (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists tenant_isolation_insert on public.%I', t);
    execute format(
      'create policy tenant_isolation_insert on public.%I for insert with check (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists tenant_isolation_update on public.%I', t);
    execute format(
      'create policy tenant_isolation_update on public.%I for update using (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context()) with check (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists tenant_isolation_delete on public.%I', t);
    execute format(
      'create policy tenant_isolation_delete on public.%I for delete using (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );

    execute format(
      'grant select, insert, update, delete on table public.%I to brain_runtime_role',
      t
    );
  end loop;
end $$;

-- Prevent a tenant-owned child ledger row from referencing an action owned by a
-- different tenant. Legacy system rows (both tenant ids null) remain valid.
create or replace function public.enforce_revenue_execution_tenant_integrity()
returns trigger
language plpgsql
as $$
declare
  action_tenant uuid;
begin
  if tg_table_name in ('revenue_followups', 'revenue_outcome_ledger') then
    select tenant_id into action_tenant
    from public.revenue_execution_actions
    where id = new.action_id;

    if not found then
      raise exception 'revenue action is not visible in the current tenant/service context';
    end if;
    if new.tenant_id is distinct from action_tenant then
      raise exception 'revenue child tenant_id must match action tenant_id';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists revenue_followups_tenant_integrity on public.revenue_followups;
create trigger revenue_followups_tenant_integrity
before insert or update of tenant_id, action_id
on public.revenue_followups
for each row execute function public.enforce_revenue_execution_tenant_integrity();

drop trigger if exists revenue_outcome_ledger_tenant_integrity on public.revenue_outcome_ledger;
create trigger revenue_outcome_ledger_tenant_integrity
before insert or update of tenant_id, action_id
on public.revenue_outcome_ledger
for each row execute function public.enforce_revenue_execution_tenant_integrity();

comment on column public.revenue_execution_actions.tenant_id is
  'Tenant owner for approval-gated revenue execution state; stamped from verified tenant context.';