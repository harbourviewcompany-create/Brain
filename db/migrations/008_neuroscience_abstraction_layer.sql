-- Brain v0.6: neuroscience abstraction registry foundation.
-- This migration creates control-layer tables for preserving neuroscience
-- abstractions, unknown mechanisms and implementation mappings.

create table if not exists neuro_abstractions (
    id uuid primary key default gen_random_uuid(),
    abstraction_id text unique not null,
    name text not null,
    scale_level text not null,
    biological_analogy text not null,
    brain_region_or_system text not null,
    computational_interpretation text not null,
    mechanism_certainty text not null check (
        mechanism_certainty in ('implemented','provisional','disputed','unknown','speculative')
    ),
    unknowns jsonb not null default '[]'::jsonb,
    competing_theories jsonb not null default '[]'::jsonb,
    software_equivalent text not null,
    owner_object text not null,
    runtime_service text not null,
    database_table text not null,
    state_machine text not null,
    formulas_or_algorithms jsonb not null default '[]'::jsonb,
    fixture_id text not null,
    test_id text not null,
    dashboard text not null,
    failure_modes jsonb not null default '[]'::jsonb,
    acceptance_criteria jsonb not null default '[]'::jsonb,
    go_hold_status text not null check (go_hold_status in ('GO','HOLD')),
    source_event_ids uuid[] not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists neuro_scale_levels (
    id uuid primary key default gen_random_uuid(),
    scale_level text unique not null,
    name text not null,
    purpose text not null,
    created_at timestamptz not null default now()
);

create table if not exists implementation_hypotheses (
    id uuid primary key default gen_random_uuid(),
    abstraction_id text not null references neuro_abstractions(abstraction_id),
    hypothesis text not null,
    theory_refs jsonb not null default '[]'::jsonb,
    status text not null default 'proposed' check (
        status in ('proposed','testing','supported','rejected','superseded')
    ),
    evidence_refs jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists mechanistic_gaps (
    id uuid primary key default gen_random_uuid(),
    abstraction_id text not null references neuro_abstractions(abstraction_id),
    gap text not null,
    risk text not null,
    research_debt_status text not null default 'open' check (
        research_debt_status in ('open','in_review','resolved','rejected')
    ),
    created_at timestamptz not null default now()
);

create table if not exists neuro_acceptance_reports (
    id uuid primary key default gen_random_uuid(),
    report_id text unique not null,
    slice_id text not null,
    verdict text not null check (verdict in ('GO','HOLD')),
    implemented_files jsonb not null default '[]'::jsonb,
    tests jsonb not null default '[]'::jsonb,
    fixtures jsonb not null default '[]'::jsonb,
    acceptance_evidence jsonb not null default '[]'::jsonb,
    unknowns_preserved jsonb not null default '[]'::jsonb,
    scope_preservation_check text not null check (scope_preservation_check in ('PASS','FAIL')),
    scientific_claim_check text not null check (scientific_claim_check in ('PASS','FAIL')),
    unresolved_items jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists neuro_abstractions_scale_idx
    on neuro_abstractions(scale_level, mechanism_certainty);

create index if not exists neuro_abstractions_status_idx
    on neuro_abstractions(go_hold_status, mechanism_certainty);

alter table neuro_abstractions enable row level security;
alter table neuro_scale_levels enable row level security;
alter table implementation_hypotheses enable row level security;
alter table mechanistic_gaps enable row level security;
alter table neuro_acceptance_reports enable row level security;

revoke all on table neuro_abstractions from anon, authenticated;
revoke all on table neuro_scale_levels from anon, authenticated;
revoke all on table implementation_hypotheses from anon, authenticated;
revoke all on table mechanistic_gaps from anon, authenticated;
revoke all on table neuro_acceptance_reports from anon, authenticated;
