-- Brain PR 3: tenant scope baseline for existing cognitive/economic tables.
--
-- This migration is intentionally additive. Existing Brain installations may
-- already contain global rows created before tenant ownership existed, so PR 3
-- adds nullable tenant_id columns, indexes, tenant-context helpers, and RLS
-- policy scaffolding without forcing destructive backfills or NOT NULL changes.
-- PR 4+ must backfill/validate table-specific ownership before hardening any
-- tenant_id column to NOT NULL.

create or replace function public.current_brain_tenant_id()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('brain.tenant_id', true), '')::uuid;
$$;

create or replace function public.current_brain_actor_id()
returns text
language sql
stable
as $$
  select nullif(current_setting('brain.actor_id', true), '');
$$;

create or replace function public.current_brain_service_context()
returns boolean
language sql
stable
as $$
  select case
    when to_regrole('brain_trusted_service_role') is null then false
    else pg_has_role(current_user, 'brain_trusted_service_role', 'member')
  end;
$$;

comment on function public.current_brain_tenant_id() is
  'Reads the tenant id supplied by the verified application/session for tenant-scoped Brain operations.';
comment on function public.current_brain_actor_id() is
  'Reads the actor id supplied by the verified application/session for audit and tenant policy checks.';
comment on function public.current_brain_service_context() is
  'Trusted service access is derived from PostgreSQL role membership in brain_trusted_service_role; it is not controlled by request headers or user-defined session settings.';

do $$
declare
  t text;
begin
  foreach t in array array[
    'brain_events',
    'sources',
    'observations',
    'evidence',
    'entities',
    'beliefs',
    'belief_evidence',
    'graph_nodes',
    'graph_edges',
    'rewire_events',
    'actions',
    'outcomes',
    'memory_items',
    'bitemporal_facts',
    'neuromodulator_snapshots',
    'homeostatic_snapshots',
    'cognitive_tasks',
    'cognitive_experiments',
    'cognitive_experiment_results',
    'projection_checkpoints',
    'sensory_inbox',
    'cognitive_cycle_runs',
    'predictions',
    'attribution_records',
    'working_memory_snapshots',
    'money_lane_sources',
    'money_lane_search_queries',
    'revenue_signals',
    'scored_revenue_opportunities',
    'packaged_offers',
    'revenue_experiments',
    'revenue_experiment_results',
    'daily_revenue_reports',
    'economic_objects',
    'economic_transitions',
    'economic_formula_runs'
  ] loop
    execute format(
      'alter table public.%I add column if not exists tenant_id uuid references public.tenants(id) on delete restrict',
      t
    );
    execute format(
      'create index if not exists %I on public.%I (tenant_id)',
      t || '_tenant_id_idx',
      t
    );
    execute format(
      'comment on column public.%I.tenant_id is %L',
      t,
      'Tenant owner for Brain PR 3 isolation. Nullable until legacy/global rows are backfilled and table-specific ownership is proven.'
    );
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
  end loop;
end $$;

-- Tenant-scoped natural uniqueness repair for tables that already had global
-- natural keys. Existing legacy/system rows with tenant_id is null preserve
-- their global uniqueness, while tenant-owned rows become unique per tenant.
alter table public.sources drop constraint if exists sources_key_key;
create unique index if not exists sources_system_key_unique_idx
  on public.sources(key)
  where tenant_id is null;
create unique index if not exists sources_tenant_key_unique_idx
  on public.sources(tenant_id, key)
  where tenant_id is not null;

alter table public.entities drop constraint if exists entities_kind_canonical_key_key;
create unique index if not exists entities_system_kind_key_unique_idx
  on public.entities(kind, canonical_key)
  where tenant_id is null;
create unique index if not exists entities_tenant_kind_key_unique_idx
  on public.entities(tenant_id, kind, canonical_key)
  where tenant_id is not null;

alter table public.graph_nodes drop constraint if exists graph_nodes_kind_node_key_key;
create unique index if not exists graph_nodes_system_kind_key_unique_idx
  on public.graph_nodes(kind, node_key)
  where tenant_id is null;
create unique index if not exists graph_nodes_tenant_kind_key_unique_idx
  on public.graph_nodes(tenant_id, kind, node_key)
  where tenant_id is not null;

alter table public.daily_revenue_reports drop constraint if exists daily_revenue_reports_report_date_key;
create unique index if not exists daily_revenue_reports_system_date_unique_idx
  on public.daily_revenue_reports(report_date)
  where tenant_id is null;
create unique index if not exists daily_revenue_reports_tenant_date_unique_idx
  on public.daily_revenue_reports(tenant_id, report_date)
  where tenant_id is not null;

-- projection_checkpoints keeps its legacy primary key in PR 3. Tenant-specific
-- projection checkpoint identity requires a later table-specific migration
-- because the current primary key is projection_name alone.
comment on table public.projection_checkpoints is
  'Tenant_id is added in PR 3, but the legacy projection_name primary key remains a tenant-breaking uniqueness constraint until a later projection-specific migration safely converts checkpoint identity.';

-- The existing append-only trigger on brain_events remains authoritative.
-- These comments document intentional PR 3 exclusions rather than silently
-- deciding that the concepts are out of scope.
comment on table public.money_lanes is
  'Commercial lane templates remain global/system-defined in PR 3 because lane_key is globally unique. Tenant-specific lane cloning/customization is deferred to a later commercial lane PR.';
comment on table public.neuro_abstractions is
  'Neuroscience abstraction registry remains a system control registry in PR 3. Per-tenant overlays are deferred until the control registry model is specified.';
comment on table public.neuro_scale_levels is
  'System control registry table; not tenant-owned in PR 3.';
comment on table public.implementation_hypotheses is
  'System research/control registry table; not tenant-owned in PR 3.';
comment on table public.mechanistic_gaps is
  'System research/control registry table; not tenant-owned in PR 3.';
comment on table public.neuro_acceptance_reports is
  'System acceptance/control registry table; not tenant-owned in PR 3.';

-- Runtime role requirement:
-- Backend DATABASE_URL values used by API and worker processes must connect as
-- a non-owner, non-BYPASSRLS role constrained by these policies. Internal jobs
-- that require cross-tenant service access must use a separately audited role
-- granted membership in brain_trusted_service_role. No request header or custom
-- GUC may grant service bypass.
