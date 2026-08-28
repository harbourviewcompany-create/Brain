-- Runtime privileges for tables created after migration 022.
--
-- Migration 022 grants DML by looping over `information_schema.columns` for a
-- `tenant_id` column. That loop is evaluated once, when 022 runs, so it can only
-- ever cover tables that already exist. Every table created afterwards ships with
-- RLS enabled and no grant at all, which leaves the constrained non-owner runtime
-- login (a `brain_runtime_role` member, per migration 019 and the release preflight
-- in tools/apply_migrations.py) unable to touch it. Migration 025 hit exactly this
-- and granted the three revenue tables it tenant-scoped; the tables below were
-- missed by the same reasoning.
--
-- Verified against a fresh PostgreSQL 16 with migrations 001-025 applied: as a
-- `brain_runtime_role` member, every table named here fails with
-- "permission denied for table", while granted tables such as `beliefs` succeed.
--
-- Owners bypass RLS on tables that are not FORCEd, so an installation still running
-- its API as the table owner is unaffected by the policies added here.

-- 1. Connector acquisition runtime (migration 024).
--
-- These already carry tenant_id and the full four-policy tenant isolation set from
-- 024; only the grant is missing. brain/connectors/store.py reads and writes all
-- three on every ingestion pass, and PostgresConnectorRegistry.available() probes
-- table existence only, so a constrained login reports the runtime as available and
-- then fails on first use.
do $$
declare
  t text;
begin
  foreach t in array array[
    'source_connector_runtime_state',
    'source_connector_ingestion_runs',
    'source_connector_observations'
  ] loop
    execute format(
      'grant select, insert, update, delete on table public.%I to brain_runtime_role',
      t
    );
  end loop;
end $$;

-- 2. Global money lanes (migration 006) and source reliability scores (023).
--
-- Both predate tenant ownership, carry no tenant_id, and are documented in
-- apps/api/tenant_app.py as remaining outside tenant mutation paths. They had RLS
-- enabled and *no policies*, which denies every non-owner regardless of grants.
--
-- The lane catalogue and its learned scores are global, so the split is by role
-- rather than by tenant: any runtime may read them -- MoneySpineService loads both
-- when the API builds its revenue spine -- but only the separately audited trusted
-- worker may mutate them, since a per-tenant runtime writing global learning state
-- would be a cross-tenant mutation.
do $$
declare
  t text;
begin
  foreach t in array array['money_lanes', 'revenue_source_scores'] loop
    execute format('drop policy if exists global_catalogue_read on public.%I', t);
    execute format(
      'create policy global_catalogue_read on public.%I for select using (true)',
      t
    );
    execute format('drop policy if exists global_catalogue_service_insert on public.%I', t);
    execute format(
      'create policy global_catalogue_service_insert on public.%I for insert with check (public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists global_catalogue_service_update on public.%I', t);
    execute format(
      'create policy global_catalogue_service_update on public.%I for update using (public.current_brain_service_context()) with check (public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists global_catalogue_service_delete on public.%I', t);
    execute format(
      'create policy global_catalogue_service_delete on public.%I for delete using (public.current_brain_service_context())',
      t
    );

    execute format('grant select on table public.%I to brain_runtime_role', t);
    execute format(
      'grant insert, update, delete on table public.%I to brain_trusted_service_role',
      t
    );
  end loop;
end $$;

comment on table public.money_lanes is
  'Global money lane catalogue. Readable by any Brain runtime; mutable only under trusted service context.';
comment on table public.revenue_source_scores is
  'Global per-source reliability learning. Readable by any Brain runtime; mutable only under trusted service context.';
