-- Brain v0.4: working-memory snapshots, predictions, and outcome attribution.

create table if not exists predictions (
    id uuid primary key,
    statement text not null,
    expected_value double precision not null,
    confidence double precision not null check (confidence between 0 and 1),
    horizon_seconds integer not null,
    belief_id uuid,
    action_id uuid,
    edge_ids uuid[] not null default '{}',
    source_keys text[] not null default '{}',
    status text not null default 'open'
        check (status in ('open', 'resolved', 'expired', 'cancelled')),
    created_at timestamptz not null default now(),
    resolve_by timestamptz,
    resolved_at timestamptz,
    metadata jsonb not null default '{}'::jsonb
);
create index if not exists predictions_status_resolve_by_idx
    on predictions (status, resolve_by);

create table if not exists attribution_records (
    id uuid primary key,
    outcome_id uuid not null,
    prediction_id uuid references predictions(id),
    edge_ids uuid[] not null default '{}',
    source_keys text[] not null default '{}',
    reward_score double precision not null,
    prediction_error double precision not null default 0,
    edge_deltas jsonb not null default '{}'::jsonb,
    source_deltas jsonb not null default '{}'::jsonb,
    rationale jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists attribution_records_outcome_idx
    on attribution_records (outcome_id);
create index if not exists attribution_records_prediction_idx
    on attribution_records (prediction_id);

create table if not exists working_memory_snapshots (
    id bigserial primary key,
    cycle_id uuid,
    slots jsonb not null default '[]'::jsonb,
    capacity integer not null,
    created_at timestamptz not null default now()
);

alter table predictions enable row level security;
alter table attribution_records enable row level security;
alter table working_memory_snapshots enable row level security;
revoke all on table predictions from anon, authenticated;
revoke all on table attribution_records from anon, authenticated;
revoke all on table working_memory_snapshots from anon, authenticated;
