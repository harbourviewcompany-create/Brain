-- Brain v0.3: durable sensory inbox and cognitive cycle execution ledger.

create table if not exists sensory_inbox (
    id uuid primary key default gen_random_uuid(),
    source_key text not null,
    content text not null,
    claim text not null,
    payload jsonb not null default '{}'::jsonb,
    status text not null default 'pending' check (status in ('pending','processing','completed','failed')),
    attempts integer not null default 0,
    available_at timestamptz not null default now(),
    claimed_at timestamptz,
    completed_at timestamptz,
    last_error text,
    created_at timestamptz not null default now()
);
create index if not exists sensory_inbox_pending_idx on sensory_inbox(status, available_at, created_at);

create table if not exists cognitive_cycle_runs (
    id uuid primary key,
    inbox_id uuid references sensory_inbox(id),
    observation_id uuid,
    belief_id uuid,
    evidence_id uuid,
    attention_score double precision,
    contradiction_detected boolean not null default false,
    task_ids uuid[] not null default '{}',
    event_ids uuid[] not null default '{}',
    status text not null default 'completed',
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    metadata jsonb not null default '{}'::jsonb
);
create index if not exists cognitive_cycle_runs_inbox_idx on cognitive_cycle_runs(inbox_id);

alter table sensory_inbox enable row level security;
alter table cognitive_cycle_runs enable row level security;
revoke all on table sensory_inbox from anon, authenticated;
revoke all on table cognitive_cycle_runs from anon, authenticated;
