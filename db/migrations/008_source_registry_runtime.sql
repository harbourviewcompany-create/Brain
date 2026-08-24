-- MOD-017 Persistent Source Registry and Signal Intake Runtime
-- This migration defines the durable database target for the deterministic runtime.
-- It does not activate live connectors, scraping, browser automation, paid-license ingestion, or external commercial action.

create table if not exists source_registry_sources (
  id uuid primary key,
  source_name text not null,
  source_category text not null,
  url_or_access_path text not null,
  lifecycle_status text not null,
  legal_access_status text not null,
  priority_score integer not null,
  score jsonb not null,
  jurisdiction_market_coverage jsonb not null default '[]'::jsonb,
  signal_types jsonb not null default '[]'::jsonb,
  downstream_use_cases jsonb not null default '[]'::jsonb,
  provenance_requirements jsonb not null default '[]'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists source_registry_ingestion_runs (
  run_id uuid primary key,
  source_id uuid not null references source_registry_sources(id),
  access_method text not null,
  status text not null,
  started_at timestamptz not null,
  completed_at timestamptz,
  observations_created integer not null default 0,
  error_message text
);

create table if not exists source_registry_observations (
  observation_id uuid primary key,
  source_id uuid not null references source_registry_sources(id),
  ingestion_run_id uuid references source_registry_ingestion_runs(run_id),
  source_url_or_path text not null,
  observed_at timestamptz not null,
  retrieved_at timestamptz not null,
  extract_hash_or_snapshot_id text not null,
  legal_access_status text not null,
  signal_types jsonb not null default '[]'::jsonb,
  raw_summary text not null,
  normalized_entities jsonb not null default '[]'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  confidence numeric not null check (confidence >= 0 and confidence <= 1),
  status text not null,
  unique (source_id, extract_hash_or_snapshot_id)
);

create table if not exists source_registry_signal_inbox (
  signal_id uuid primary key,
  observation_id uuid not null unique references source_registry_observations(observation_id),
  source_id uuid not null references source_registry_sources(id),
  title text not null,
  signal_types jsonb not null default '[]'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  confidence numeric not null check (confidence >= 0 and confidence <= 1),
  review_status text not null,
  routed_at timestamptz not null,
  downstream_use_cases jsonb not null default '[]'::jsonb,
  action_suggestions jsonb not null default '[]'::jsonb,
  reviewer text,
  review_note text
);

create table if not exists source_registry_health_checks (
  health_check_id uuid primary key,
  source_id uuid not null references source_registry_sources(id),
  checked_at timestamptz not null,
  status text not null,
  message text not null,
  consecutive_failures integer not null default 0,
  next_review_at timestamptz
);

create table if not exists source_registry_events (
  event_id uuid primary key,
  source_id uuid references source_registry_sources(id),
  related_object_id uuid,
  event_type text not null,
  occurred_at timestamptz not null,
  actor text not null,
  detail text not null
);

create index if not exists idx_source_registry_sources_lifecycle on source_registry_sources(lifecycle_status);
create index if not exists idx_source_registry_sources_legal on source_registry_sources(legal_access_status);
create index if not exists idx_source_registry_runs_source on source_registry_ingestion_runs(source_id);
create index if not exists idx_source_registry_observations_source on source_registry_observations(source_id);
create index if not exists idx_source_registry_signal_status on source_registry_signal_inbox(review_status);
create index if not exists idx_source_registry_health_source on source_registry_health_checks(source_id);
create index if not exists idx_source_registry_events_source on source_registry_events(source_id);
