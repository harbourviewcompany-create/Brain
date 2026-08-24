create table if not exists public.global_workspace_frames (
    id uuid primary key default gen_random_uuid(),
    frame_key text not null unique,
    active_goals jsonb not null default '[]'::jsonb,
    active_memories jsonb not null default '[]'::jsonb,
    active_conflicts jsonb not null default '[]'::jsonb,
    top_signals jsonb not null default '[]'::jsonb,
    selected_interpretation jsonb not null default '{}'::jsonb,
    suppressed_alternatives jsonb not null default '[]'::jsonb,
    uncertainty_map jsonb not null default '{}'::jsonb,
    affective_or_modulatory_state jsonb not null default '{}'::jsonb,
    available_actions jsonb not null default '[]'::jsonb,
    approval_constraints jsonb not null default '[]'::jsonb,
    predicted_consequences jsonb not null default '[]'::jsonb,
    current_self_state jsonb not null default '{}'::jsonb,
    current_world_state jsonb not null default '{}'::jsonb,
    explanation_trace jsonb not null default '[]'::jsonb,
    consciousness_claim boolean not null default false check (consciousness_claim = false),
    go_hold_status text not null default 'GO' check (go_hold_status in ('GO', 'HOLD')),
    created_at timestamptz not null default now()
);

create table if not exists public.workspace_items (
    id uuid primary key default gen_random_uuid(),
    frame_id uuid references public.global_workspace_frames(id) on delete cascade,
    content_ref text not null,
    priority numeric not null,
    evidence_refs jsonb not null,
    proposing_module text not null,
    selected boolean not null default false,
    suppressed boolean not null default false,
    created_at timestamptz not null default now(),
    check (jsonb_typeof(evidence_refs) = 'array'),
    check (jsonb_array_length(evidence_refs) > 0)
);

create table if not exists public.workspace_broadcasts (
    id uuid primary key default gen_random_uuid(),
    frame_id uuid references public.global_workspace_frames(id) on delete cascade,
    winner_item_id uuid references public.workspace_items(id),
    consumer_modules jsonb not null,
    suppressed_item_ids jsonb not null default '[]'::jsonb,
    evidence_refs jsonb not null,
    consciousness_claim boolean not null default false check (consciousness_claim = false),
    created_at timestamptz not null default now(),
    check (jsonb_typeof(consumer_modules) = 'array'),
    check (jsonb_array_length(consumer_modules) > 0),
    check (jsonb_typeof(evidence_refs) = 'array'),
    check (jsonb_array_length(evidence_refs) > 0)
);

create table if not exists public.workspace_access_decisions (
    id uuid primary key default gen_random_uuid(),
    frame_id uuid references public.global_workspace_frames(id) on delete cascade,
    decision_rule text not null,
    input_scores jsonb not null default '{}'::jsonb,
    winner_item_id uuid references public.workspace_items(id),
    rejected_alternatives jsonb not null default '[]'::jsonb,
    audit_event_ids jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

alter table public.global_workspace_frames enable row level security;
alter table public.workspace_items enable row level security;
alter table public.workspace_broadcasts enable row level security;
alter table public.workspace_access_decisions enable row level security;

revoke all on public.global_workspace_frames from anon, authenticated;
revoke all on public.workspace_items from anon, authenticated;
revoke all on public.workspace_broadcasts from anon, authenticated;
revoke all on public.workspace_access_decisions from anon, authenticated;
