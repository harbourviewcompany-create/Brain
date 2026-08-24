-- Brain v0.9: durable generic cognitive object repository.
-- Used for provenance-rich world, memory, benchmark, planning and model-cortex state.

create table if not exists cognitive_objects (
    object_id text not null,
    kind text not null,
    payload jsonb not null,
    source_refs text[] not null default '{}',
    world_valid_from timestamptz,
    world_valid_to timestamptz,
    learned_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (object_id, kind)
);

create index if not exists cognitive_objects_kind_idx
    on cognitive_objects(kind, updated_at desc);

create index if not exists cognitive_objects_world_time_idx
    on cognitive_objects(kind, world_valid_from, world_valid_to);

alter table cognitive_objects enable row level security;
revoke all on table cognitive_objects from anon, authenticated;
