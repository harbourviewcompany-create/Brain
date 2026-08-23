create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists brain_events (
  id uuid primary key default gen_random_uuid(),
  event_type text not null,
  aggregate_type text not null,
  aggregate_id uuid not null,
  causation_id uuid,
  correlation_id uuid,
  payload jsonb not null,
  occurred_at timestamptz not null default now()
);
create index if not exists brain_events_aggregate_idx on brain_events(aggregate_type, aggregate_id, occurred_at);
create index if not exists brain_events_type_idx on brain_events(event_type, occurred_at);

create table if not exists sources (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  name text not null,
  authority_score double precision not null default 0.5 check (authority_score between 0 and 1),
  historical_utility double precision not null default 0.5 check (historical_utility between 0 and 1),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists observations (
  id uuid primary key default gen_random_uuid(),
  source_id uuid references sources(id),
  content text not null,
  content_hash text,
  observed_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(1536)
);

create table if not exists evidence (
  id uuid primary key default gen_random_uuid(),
  observation_id uuid references observations(id),
  claim text not null,
  reliability double precision not null check (reliability between 0 and 1),
  stance text not null default 'neutral',
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists entities (
  id uuid primary key default gen_random_uuid(),
  kind text not null,
  canonical_key text not null,
  properties jsonb not null default '{}'::jsonb,
  confidence double precision not null default 0.5 check (confidence between 0 and 1),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(kind, canonical_key)
);

create table if not exists beliefs (
  id uuid primary key default gen_random_uuid(),
  statement text not null,
  confidence double precision not null default 0.5 check (confidence between 0 and 1),
  state text not null default 'hypothesis',
  unknowns jsonb not null default '[]'::jsonb,
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists belief_evidence (
  belief_id uuid not null references beliefs(id) on delete cascade,
  evidence_id uuid not null references evidence(id) on delete cascade,
  relation text not null check (relation in ('supports','contradicts')),
  primary key (belief_id, evidence_id)
);

create table if not exists graph_nodes (
  id uuid primary key,
  kind text not null,
  node_key text not null,
  properties jsonb not null default '{}'::jsonb,
  unique(kind, node_key)
);

create table if not exists graph_edges (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references graph_nodes(id),
  target_id uuid not null references graph_nodes(id),
  relation text not null,
  weight double precision not null default 0.5 check (weight between 0 and 1),
  confidence double precision not null default 0.5 check (confidence between 0 and 1),
  evidence_ids uuid[] not null default '{}',
  updated_at timestamptz not null default now()
);

create table if not exists rewire_events (
  id uuid primary key default gen_random_uuid(),
  operation text not null,
  target_id uuid not null,
  reason text not null,
  previous jsonb not null default '{}'::jsonb,
  current jsonb not null default '{}'::jsonb,
  evidence_ids uuid[] not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists actions (
  id uuid primary key default gen_random_uuid(),
  description text not null,
  expected_value double precision not null default 0,
  uncertainty double precision not null default 0.5,
  external boolean not null default false,
  status text not null default 'proposed',
  rationale jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists outcomes (
  id uuid primary key default gen_random_uuid(),
  action_id uuid not null references actions(id),
  value_created double precision not null default 0,
  operator_time_cost double precision not null default 0,
  prediction_accuracy double precision not null default 0,
  trust_impact double precision not null default 0,
  legal_risk double precision not null default 0,
  created_at timestamptz not null default now()
);

-- Treat the event ledger as append-only at the application role layer.
-- Production RLS/policies should expose no direct client writes to cognitive tables.
