-- NEURO-004/005 unknown mechanism and theory conflict registry.
-- These tables preserve uncertainty and theory conflict without claiming solved neuroscience.

create table if not exists public.neuro_unknown_mechanisms (
    id uuid primary key default gen_random_uuid(),
    unknown_id text not null unique,
    name text not null,
    kind text not null,
    related_abstraction_ids text[] not null default '{}',
    current_claim_boundary text not null,
    forbidden_claims jsonb not null default '[]'::jsonb,
    allowed_uses jsonb not null default '[]'::jsonb,
    evidence_needed jsonb not null default '[]'::jsonb,
    research_questions jsonb not null default '[]'::jsonb,
    owner_object text not null,
    runtime_service text not null,
    fixture_id text not null,
    test_id text not null,
    dashboard text not null,
    go_hold_status text not null check (go_hold_status = 'HOLD'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.neuro_theories (
    id uuid primary key default gen_random_uuid(),
    theory_id text not null unique,
    name text not null,
    mechanism_area text not null,
    claim text not null,
    status text not null,
    implementation_posture text not null,
    competing_theory_ids text[] not null default '{}',
    linked_unknown_ids text[] not null default '{}',
    supporting_evidence jsonb not null default '[]'::jsonb,
    contradicting_evidence jsonb not null default '[]'::jsonb,
    claim_boundary text not null,
    owner_object text not null,
    runtime_service text not null,
    fixture_id text not null,
    test_id text not null,
    dashboard text not null,
    acceptance_criteria jsonb not null default '[]'::jsonb,
    go_hold_status text not null check (go_hold_status in ('GO', 'HOLD')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.neuro_theory_conflicts (
    id uuid primary key default gen_random_uuid(),
    conflict_id text not null unique,
    theory_ids text[] not null,
    conflict_summary text not null,
    resolution_rule text not null,
    operator_surface text not null,
    acceptance_criteria jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_neuro_unknown_kind
    on public.neuro_unknown_mechanisms(kind);

create index if not exists idx_neuro_theory_status
    on public.neuro_theories(status);

create index if not exists idx_neuro_theory_conflict_ids
    on public.neuro_theory_conflicts using gin(theory_ids);

alter table public.neuro_unknown_mechanisms enable row level security;
alter table public.neuro_theories enable row level security;
alter table public.neuro_theory_conflicts enable row level security;

revoke all on public.neuro_unknown_mechanisms from anon, authenticated;
revoke all on public.neuro_theories from anon, authenticated;
revoke all on public.neuro_theory_conflicts from anon, authenticated;

comment on table public.neuro_unknown_mechanisms is
    'HOLD-only neuroscience unknown, disputed and speculative mechanism records.';

comment on table public.neuro_theories is
    'Bounded neuroscience theory records with evidence, conflict and implementation posture.';

comment on table public.neuro_theory_conflicts is
    'Explicit theory conflicts that must not be silently resolved by agents.';
