-- Brain Runtime v0.2: memory systems, bitemporal cognition, modulation,
-- homeostasis, scheduling, experiments, and replay checkpoints.

create table if not exists memory_items (
    id uuid primary key,
    kind text not null check (kind in ('sensory','working','episodic','semantic','procedural','prospective')),
    content jsonb not null,
    salience double precision not null default 0.5 check (salience between 0 and 1),
    strength double precision not null default 0.5 check (strength between 0 and 1),
    source_event_ids uuid[] not null default '{}',
    created_at timestamptz not null default now(),
    last_accessed_at timestamptz not null default now(),
    access_count bigint not null default 0
);

create index if not exists memory_items_kind_strength_idx
    on memory_items (kind, strength desc);

create table if not exists bitemporal_facts (
    id uuid primary key,
    subject_id uuid not null,
    predicate text not null,
    object jsonb not null,
    valid_from timestamptz not null,
    valid_to timestamptz,
    known_from timestamptz not null default now(),
    known_to timestamptz,
    source_event_ids uuid[] not null default '{}',
    metadata jsonb not null default '{}'
);

create index if not exists bitemporal_facts_subject_predicate_idx
    on bitemporal_facts (subject_id, predicate, valid_from desc, known_from desc);

create table if not exists neuromodulator_snapshots (
    id bigserial primary key,
    dopamine double precision not null check (dopamine between 0 and 1),
    norepinephrine double precision not null check (norepinephrine between 0 and 1),
    serotonin double precision not null check (serotonin between 0 and 1),
    acetylcholine double precision not null check (acetylcholine between 0 and 1),
    stress double precision not null check (stress between 0 and 1),
    reason jsonb not null default '{}',
    created_at timestamptz not null default now()
);

create table if not exists homeostatic_snapshots (
    id bigserial primary key,
    compute_load double precision not null default 0,
    unresolved_uncertainty double precision not null default 0,
    memory_pressure double precision not null default 0,
    operator_load double precision not null default 0,
    budget_pressure double precision not null default 0,
    graph_density_pressure double precision not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists cognitive_tasks (
    id uuid primary key,
    name text not null,
    payload jsonb not null default '{}',
    utility double precision not null,
    urgency double precision not null,
    novelty double precision not null,
    uncertainty_reduction double precision not null,
    cost double precision not null,
    status text not null default 'pending',
    selected_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists cognitive_tasks_status_created_idx
    on cognitive_tasks (status, created_at);

create table if not exists cognitive_experiments (
    id uuid primary key,
    name text not null,
    policy_name text not null,
    metadata jsonb not null default '{}',
    created_at timestamptz not null default now()
);

create table if not exists cognitive_experiment_results (
    id bigserial primary key,
    experiment_id uuid not null references cognitive_experiments(id) on delete cascade,
    score double precision not null,
    metrics jsonb not null default '{}',
    final_state jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists projection_checkpoints (
    projection_name text primary key,
    last_event_id uuid,
    event_count bigint not null default 0,
    state jsonb not null default '{}',
    updated_at timestamptz not null default now()
);

-- These tables are internal cognitive state. Keep them out of exposed schemas in
-- production when possible. If exposed through Supabase Data API, enable RLS and
-- grant only the exact roles required by the control plane.
