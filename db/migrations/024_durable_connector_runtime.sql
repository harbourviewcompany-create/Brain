-- Durable connector acquisition runtime.
--
-- This is the restart-safe operational layer between configured external connectors
-- and Brain's sensory stream. It intentionally does not replace MOD-017's normalized
-- source_registry_* intelligence tables: these rows are raw acquisition state and
-- provenance. A later normalization bridge may promote captured observations into the
-- intelligence registry once source authority and mapping are explicit.
--
-- Depends on tenant/RLS foundation migrations 019-023. System/global connector rows
-- use tenant_id IS NULL and are accessible to the separately audited trusted worker
-- through current_brain_service_context(). Tenant-owned connector rows are isolated by
-- the same RLS model used by the rest of Brain.

create table if not exists public.source_connector_runtime_state (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.tenants(id) on delete restrict,
  source_key text not null check (length(trim(source_key)) > 0),
  source_name text not null check (length(trim(source_name)) > 0),
  url text not null check (length(trim(url)) > 0),
  connector_kind text not null check (connector_kind in ('rss','atom','http_json','http_text')),
  access_disposition text not null check (
    access_disposition in ('allowed','rate_limited','manual_only','prohibited','unknown')
  ),
  refresh_seconds integer not null default 300 check (refresh_seconds >= 30),
  enabled boolean not null default true,
  public_config jsonb not null default '{}'::jsonb,
  last_fetched_at timestamptz,
  last_success_at timestamptz,
  consecutive_failures integer not null default 0 check (consecutive_failures >= 0),
  next_due_at timestamptz not null default now(),
  lease_owner text,
  lease_expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists source_connector_runtime_system_key_unique_idx
  on public.source_connector_runtime_state(source_key)
  where tenant_id is null;
create unique index if not exists source_connector_runtime_tenant_key_unique_idx
  on public.source_connector_runtime_state(tenant_id, source_key)
  where tenant_id is not null;
create index if not exists source_connector_runtime_due_idx
  on public.source_connector_runtime_state(next_due_at, source_key)
  where enabled = true;
create index if not exists source_connector_runtime_lease_idx
  on public.source_connector_runtime_state(lease_expires_at)
  where lease_owner is not null;

create table if not exists public.source_connector_ingestion_runs (
  run_id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.tenants(id) on delete restrict,
  source_id uuid not null references public.source_connector_runtime_state(id) on delete cascade,
  connector_kind text not null,
  status text not null check (status in ('started','success','empty','partial','failed','skipped')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  retrieved_at timestamptz,
  fetched_count integer not null default 0 check (fetched_count >= 0),
  enqueued_count integer not null default 0 check (enqueued_count >= 0),
  deduped_count integer not null default 0 check (deduped_count >= 0),
  http_status integer,
  duration_ms double precision not null default 0 check (duration_ms >= 0),
  error_message text
);

create index if not exists source_connector_runs_source_started_idx
  on public.source_connector_ingestion_runs(source_id, started_at desc);
create index if not exists source_connector_runs_tenant_started_idx
  on public.source_connector_ingestion_runs(tenant_id, started_at desc);

create table if not exists public.source_connector_observations (
  observation_id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.tenants(id) on delete restrict,
  source_id uuid not null references public.source_connector_runtime_state(id) on delete cascade,
  ingestion_run_id uuid references public.source_connector_ingestion_runs(run_id) on delete set null,
  item_id text not null,
  content_hash text not null check (length(trim(content_hash)) > 0),
  source_url text not null check (length(trim(source_url)) > 0),
  title text not null default '',
  raw_content text not null,
  claim text not null,
  observed_at timestamptz not null,
  retrieved_at timestamptz not null,
  confidence double precision not null default 0.5 check (confidence >= 0 and confidence <= 1),
  signal_hints jsonb not null default '[]'::jsonb,
  entities jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  status text not null default 'captured' check (status in ('captured','enqueued')),
  inbox_id uuid,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  seen_count integer not null default 1 check (seen_count >= 1),
  unique (source_id, content_hash)
);

create index if not exists source_connector_observations_source_seen_idx
  on public.source_connector_observations(source_id, last_seen_at desc);
create index if not exists source_connector_observations_tenant_seen_idx
  on public.source_connector_observations(tenant_id, last_seen_at desc);
create index if not exists source_connector_observations_status_idx
  on public.source_connector_observations(status, last_seen_at desc);

-- Runtime config is deliberately public/non-secret connector configuration only.
-- Authorization headers, bearer tokens, API keys and cookies belong in credential
-- injection, never in this database JSON.
comment on column public.source_connector_runtime_state.public_config is
  'Non-secret connector parsing/configuration only. Credentials, Authorization headers, API keys, tokens and cookies must not be persisted here.';
comment on table public.source_connector_observations is
  'Raw restart-safe connector acquisition ledger. It preserves provenance before sensory enqueue and is distinct from normalized MOD-017 source_registry_observations.';

-- Match the tenant isolation contract used by migrations 020-023.
do $$
declare
  t text;
begin
  foreach t in array array[
    'source_connector_runtime_state',
    'source_connector_ingestion_runs',
    'source_connector_observations'
  ] loop
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
