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
  select coalesce(nullif(current_setting('brain.service_context', true), '')::boolean, false);
$$;

comment on function public.current_brain_tenant_id() is
  'Reads the tenant id supplied by the application/session for tenant-scoped Brain operations.';
comment on function public.current_brain_actor_id() is
  'Reads the actor id supplied by the application/session for audit and tenant policy checks.';
comment on function public.current_brain_service_context() is
  'Reads whether the current operation is an internal service context. This is not a public bypass.';

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

    execute format('drop policy if exists tenant_isolation_select on public.%I', t);
    execute format(
      'create policy tenant_isolation_select on public.%I for select using (public.current_brain_service_context() or tenant_id = public.current_brain_tenant_id())',
      t
    );

    execute format('drop policy if exists tenant_isolation_insert on public.%I', t);
    execute format(
      'create policy tenant_isolation_insert on public.%I for insert with check (public.current_brain_service_context() or tenant_id = public.current_brain_tenant_id())',
      t
    );

    execute format('drop policy if exists tenant_isolation_update on public.%I', t);
    execute format(
      'create policy tenant_isolation_update on public.%I for update using (public.current_brain_service_context() or tenant_id = public.current_brain_tenant_id()) with check (public.current_brain_service_context() or tenant_id = public.current_brain_tenant_id())',
      t
    );

    execute format('drop policy if exists tenant_isolation_delete on public.%I', t);
    execute format(
      'create policy tenant_isolation_delete on public.%I for delete using (public.current_brain_service_context() or tenant_id = public.current_brain_tenant_id())',
      t
    );
  end loop;
end $$;

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
