create table if not exists public.economic_objects (
    kind text not null,
    id uuid not null,
    payload jsonb not null,
    updated_at timestamptz not null default now(),
    primary key (kind, id)
);

create index if not exists economic_objects_kind_updated_idx
    on public.economic_objects (kind, updated_at desc);

create table if not exists public.economic_transitions (
    id uuid primary key,
    object_id uuid not null,
    object_type text not null,
    from_state text not null,
    to_state text not null,
    trigger text not null,
    actor text not null,
    evidence_ids uuid[] not null default '{}',
    formula_run_ids uuid[] not null default '{}',
    acceptance_test text not null,
    created_at timestamptz not null default now()
);

create index if not exists economic_transitions_object_idx
    on public.economic_transitions (object_id, created_at asc);

create table if not exists public.economic_formula_runs (
    id uuid primary key,
    formula_id text not null,
    owner_object_id text not null,
    owner_object_type text not null,
    inputs jsonb not null,
    output double precision not null,
    service text not null,
    table_store text not null,
    dashboard text not null,
    decision_consequence text not null,
    audit_evidence jsonb not null,
    created_at timestamptz not null default now()
);

create index if not exists economic_formula_owner_idx
    on public.economic_formula_runs (owner_object_type, owner_object_id, created_at desc);

comment on table public.economic_objects is
    'Canonical durable object ledger for MOD-008 through MOD-015 economic cognition.';
comment on table public.economic_transitions is
    'Auditable state transitions for pressure, money paths, counterparties, transactions, attribution and compounding.';
comment on table public.economic_formula_runs is
    'Traceable formula evidence for economic scores and consequential prioritization.';
