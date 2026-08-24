create table if not exists public.memory_system_records (
    id uuid primary key default gen_random_uuid(),
    memory_key text not null unique,
    memory_kind text not null,
    content_ref text not null,
    evidence_refs jsonb not null,
    source_refs jsonb not null,
    provenance text not null,
    confidence numeric not null check (confidence >= 0 and confidence <= 1),
    retrieval_cues jsonb not null default '[]'::jsonb,
    linked_workspace_frame_ids jsonb not null default '[]'::jsonb,
    linked_memory_ids jsonb not null default '[]'::jsonb,
    contradiction_refs jsonb not null default '[]'::jsonb,
    lifecycle_state text not null default 'encoded',
    retention_policy text not null,
    replay_required boolean not null default false,
    quarantine_reason text,
    go_hold_status text not null default 'GO' check (go_hold_status in ('GO', 'HOLD')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (jsonb_typeof(evidence_refs) = 'array'),
    check (jsonb_array_length(evidence_refs) > 0),
    check (jsonb_typeof(source_refs) = 'array'),
    check (jsonb_array_length(source_refs) > 0),
    check (lifecycle_state in ('encoded','retrievable','consolidated','reconsolidated','decay_candidate','forgotten','quarantined')),
    check (retention_policy in ('retain','decay','forget','quarantine','operator_review')),
    check (lifecycle_state <> 'quarantined' or (go_hold_status = 'HOLD' and quarantine_reason is not null)),
    check (retention_policy <> 'forget' or replay_required = false)
);

create table if not exists public.memory_consolidation_events (
    id uuid primary key default gen_random_uuid(),
    event_key text not null unique,
    operation text not null check (operation in ('consolidate','reconsolidate','decay','forget','quarantine','replay')),
    input_memory_ids jsonb not null,
    output_memory_ids jsonb not null default '[]'::jsonb,
    evidence_refs jsonb not null,
    operator_review_required boolean not null default false,
    audit_event text not null,
    created_at timestamptz not null default now(),
    check (jsonb_typeof(input_memory_ids) = 'array'),
    check (jsonb_array_length(input_memory_ids) > 0),
    check (jsonb_typeof(evidence_refs) = 'array'),
    check (jsonb_array_length(evidence_refs) > 0)
);

create table if not exists public.memory_links (
    id uuid primary key default gen_random_uuid(),
    source_memory_id uuid references public.memory_system_records(id) on delete cascade,
    target_memory_id uuid references public.memory_system_records(id) on delete cascade,
    link_kind text not null,
    evidence_refs jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.memory_quarantine_decisions (
    id uuid primary key default gen_random_uuid(),
    memory_id uuid references public.memory_system_records(id) on delete cascade,
    reason text not null,
    reviewer text,
    decision text not null default 'hold' check (decision in ('hold','restore_with_evidence','reject')),
    evidence_refs jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

alter table public.memory_system_records enable row level security;
alter table public.memory_consolidation_events enable row level security;
alter table public.memory_links enable row level security;
alter table public.memory_quarantine_decisions enable row level security;

revoke all on public.memory_system_records from anon, authenticated;
revoke all on public.memory_consolidation_events from anon, authenticated;
revoke all on public.memory_links from anon, authenticated;
revoke all on public.memory_quarantine_decisions from anon, authenticated;
