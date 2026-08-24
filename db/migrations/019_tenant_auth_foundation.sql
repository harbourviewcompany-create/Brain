-- Brain PR 2: tenant/auth/membership/invite/lifecycle foundation.
-- This migration introduces tenant ownership primitives only.
-- Existing cognitive tables are not retrofitted here; PR 3 owns tenant_id/RLS
-- migration for existing Brain state.

create table if not exists tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) > 0),
  slug text not null unique check (length(trim(slug)) > 0),
  status text not null default 'active' check (status in ('active','suspended','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz
);

create table if not exists tenant_memberships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  user_id text not null check (length(trim(user_id)) > 0),
  role text not null check (role in ('owner','admin','operator','viewer')),
  status text not null default 'active' check (status in ('active','removed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  removed_at timestamptz,
  unique (tenant_id, user_id)
);

create table if not exists tenant_invites (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  email text not null check (length(trim(email)) > 0),
  role text not null check (role in ('owner','admin','operator','viewer')),
  token_hash text not null unique,
  invited_by_user_id text not null check (length(trim(invited_by_user_id)) > 0),
  status text not null default 'pending' check (status in ('pending','accepted','revoked','expired')),
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  accepted_by_user_id text,
  accepted_at timestamptz,
  revoked_at timestamptz
);

create table if not exists tenant_audit_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  actor_user_id text not null check (length(trim(actor_user_id)) > 0),
  event_type text not null check (length(trim(event_type)) > 0),
  entity_type text not null check (length(trim(entity_type)) > 0),
  entity_id text not null check (length(trim(entity_id)) > 0),
  reason text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists tenant_memberships_tenant_role_idx
  on tenant_memberships (tenant_id, role, status);
create index if not exists tenant_memberships_user_idx
  on tenant_memberships (user_id, status);
create index if not exists tenant_invites_tenant_status_idx
  on tenant_invites (tenant_id, status, expires_at);
create index if not exists tenant_audit_events_tenant_created_idx
  on tenant_audit_events (tenant_id, created_at desc);

alter table tenants enable row level security;
alter table tenant_memberships enable row level security;
alter table tenant_invites enable row level security;
alter table tenant_audit_events enable row level security;

revoke all on table tenants from anon, authenticated;
revoke all on table tenant_memberships from anon, authenticated;
revoke all on table tenant_invites from anon, authenticated;
revoke all on table tenant_audit_events from anon, authenticated;

-- Invariant: one active owner must remain per tenant. The application service
-- enforces last-owner protection; this index makes active-owner discovery fast.
create index if not exists tenant_memberships_active_owner_idx
  on tenant_memberships (tenant_id)
  where role = 'owner' and status = 'active';

-- Store token hashes only. Plain invite tokens must not be persisted.
comment on column tenant_invites.token_hash is
  'Hash of invite token. Plain invite tokens must never be stored.';
comment on table tenants is
  'PR 2 tenant lifecycle root. Existing cognitive tables are scoped in PR 3.';
comment on table tenant_memberships is
  'PR 2 tenant membership and role foundation. Last-owner protection is application-enforced.';
comment on table tenant_audit_events is
  'Append-only tenant/auth lifecycle audit events.';
