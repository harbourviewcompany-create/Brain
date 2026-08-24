-- Brain v0.7: brain-region software maps and multi-scale cognition stack.
-- These are functional software mappings, not biological equivalence claims.

create table if not exists brain_region_maps (
    id uuid primary key default gen_random_uuid(),
    region_id text unique not null,
    name text not null,
    biological_scope text not null,
    software_equivalent text not null,
    owner_object text not null,
    runtime_service text not null,
    database_table text not null,
    signals_handled jsonb not null default '[]'::jsonb,
    implemented_state text not null check (implemented_state in ('mapped','partial','research_debt')),
    does_not_claim_literal_equivalence boolean not null default true,
    failure_modes jsonb not null default '[]'::jsonb,
    dashboard text not null,
    acceptance_criteria jsonb not null default '[]'::jsonb,
    source_event_ids uuid[] not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists multiscale_cognition_levels (
    id uuid primary key default gen_random_uuid(),
    level_id text unique not null,
    name text not null,
    scope text not null,
    software_equivalent text not null,
    owner_object text not null,
    runtime_service text not null,
    database_table text not null,
    state_machine text not null,
    interfaces_up jsonb not null default '[]'::jsonb,
    interfaces_down jsonb not null default '[]'::jsonb,
    dashboard text not null,
    acceptance_criteria jsonb not null default '[]'::jsonb,
    does_not_claim_complete_equivalence boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists multiscale_cognition_dependencies (
    id uuid primary key default gen_random_uuid(),
    source_level text not null,
    target_level text not null,
    relation text not null,
    evidence_required text not null,
    created_at timestamptz not null default now()
);

alter table brain_region_maps enable row level security;
alter table multiscale_cognition_levels enable row level security;
alter table multiscale_cognition_dependencies enable row level security;

revoke all on table brain_region_maps from anon, authenticated;
revoke all on table multiscale_cognition_levels from anon, authenticated;
revoke all on table multiscale_cognition_dependencies from anon, authenticated;
