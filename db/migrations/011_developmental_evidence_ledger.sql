create table if not exists public.developmental_evidence_objects (
    kind text not null,
    id uuid not null,
    payload jsonb not null,
    updated_at timestamptz not null default now(),
    primary key (kind, id)
);

create table if not exists public.developmental_evidence_events (
    sequence bigint generated always as identity primary key,
    id uuid not null default gen_random_uuid() unique,
    event_type text not null,
    record_kind text not null,
    record_id uuid not null,
    payload jsonb not null,
    evidence_refs text[] not null default '{}',
    created_at timestamptz not null default now()
);

create index if not exists idx_developmental_evidence_objects_kind
    on public.developmental_evidence_objects (kind, updated_at);

create index if not exists idx_developmental_evidence_events_record
    on public.developmental_evidence_events (record_kind, record_id, sequence);

create index if not exists idx_developmental_evidence_events_type
    on public.developmental_evidence_events (event_type, sequence);

comment on table public.developmental_evidence_objects is
    'Latest typed snapshots for developmental/metacognitive evidence records.';
comment on table public.developmental_evidence_events is
    'Append-only ordered developmental evidence history; do not update/delete as normal runtime behavior.';
