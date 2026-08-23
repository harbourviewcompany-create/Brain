-- Brain v0.8: controlled developmental intelligence persistence.
-- All state below is internal cognitive state. Consequential external actions
-- remain approval-gated outside this schema.

create table if not exists brain_migration_ledger (
    migration_key text primary key,
    checksum_sha256 text,
    applied_at timestamptz not null default now(),
    applied_by text,
    environment text,
    evidence jsonb not null default '{}'::jsonb
);

create table if not exists developmental_objects (
    object_id text not null,
    kind text not null,
    payload jsonb not null,
    source_refs text[] not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (object_id, kind)
);
create index if not exists developmental_objects_kind_idx
    on developmental_objects(kind, updated_at);

create table if not exists developmental_transitions (
    id uuid primary key default gen_random_uuid(),
    module_key text not null,
    previous_state text not null,
    new_state text not null,
    evidence_refs text[] not null default '{}',
    reason text not null,
    created_at timestamptz not null default now()
);
create index if not exists developmental_transitions_module_idx
    on developmental_transitions(module_key, created_at);

create table if not exists developmental_scores (
    id uuid primary key default gen_random_uuid(),
    module_key text not null,
    score double precision not null check (score between 0 and 1),
    dimensions jsonb not null,
    created_at timestamptz not null default now()
);
create index if not exists developmental_scores_module_idx
    on developmental_scores(module_key, created_at desc);

create table if not exists model_performance_events (
    id uuid primary key default gen_random_uuid(),
    provider text not null,
    model text not null,
    task_type text not null,
    predicted_confidence double precision,
    realized_accuracy double precision,
    latency_ms double precision,
    cost_amount double precision,
    evidence_refs text[] not null default '{}',
    created_at timestamptz not null default now()
);

create table if not exists cognitive_trace_events (
    id uuid primary key default gen_random_uuid(),
    trace_id uuid not null,
    parent_span_id uuid,
    span_name text not null,
    category text not null,
    status text not null,
    attributes jsonb not null default '{}'::jsonb,
    started_at timestamptz not null,
    ended_at timestamptz
);
create index if not exists cognitive_trace_events_trace_idx
    on cognitive_trace_events(trace_id, started_at);

alter table brain_migration_ledger enable row level security;
alter table developmental_objects enable row level security;
alter table developmental_transitions enable row level security;
alter table developmental_scores enable row level security;
alter table model_performance_events enable row level security;
alter table cognitive_trace_events enable row level security;

revoke all on table brain_migration_ledger from anon, authenticated;
revoke all on table developmental_objects from anon, authenticated;
revoke all on table developmental_transitions from anon, authenticated;
revoke all on table developmental_scores from anon, authenticated;
revoke all on table model_performance_events from anon, authenticated;
revoke all on table cognitive_trace_events from anon, authenticated;
