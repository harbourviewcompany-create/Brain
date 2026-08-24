-- Cognitive Organism persistence hardening.
-- Functional consciousness proxy only. No literal consciousness claim.

create table if not exists cognitive_organism_checkpoints (
  checkpoint_name text primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table cognitive_organism_checkpoints enable row level security;
alter table organism_audit_events enable row level security;

revoke all on cognitive_organism_checkpoints from public;
revoke all on organism_audit_events from public;

create index if not exists idx_organism_audit_events_type_time
  on organism_audit_events (event_type, created_at desc);

create index if not exists idx_organism_audit_events_object_time
  on organism_audit_events (object_type, object_id, created_at desc);
