-- Brain tenant runtime enforcement.
-- Makes tenant stamping the default for tenant-owned runtime tables and exposes
-- only self-membership lookup under verified tenant/actor transaction context.

alter table public.tenants force row level security;
alter table public.tenant_memberships force row level security;
alter table public.tenant_invites force row level security;
alter table public.tenant_audit_events force row level security;

drop policy if exists tenant_self_select on public.tenants;
create policy tenant_self_select on public.tenants for select
  using (id = public.current_brain_tenant_id() or public.current_brain_service_context());

drop policy if exists membership_self_select on public.tenant_memberships;
create policy membership_self_select on public.tenant_memberships for select
  using (
    (tenant_id = public.current_brain_tenant_id() and user_id = public.current_brain_actor_id())
    or public.current_brain_service_context()
  );

drop policy if exists tenant_invites_service_only on public.tenant_invites;
create policy tenant_invites_service_only on public.tenant_invites for all
  using (public.current_brain_service_context())
  with check (public.current_brain_service_context());

drop policy if exists tenant_audit_service_only on public.tenant_audit_events;
create policy tenant_audit_service_only on public.tenant_audit_events for all
  using (public.current_brain_service_context())
  with check (public.current_brain_service_context());

-- Existing adapters omit tenant_id in insert lists. Stamping from the verified
-- transaction-local tenant context makes those writes tenant-owned by default.
do $$
declare
  r record;
begin
  for r in
    select table_name
    from information_schema.columns
    where table_schema = 'public'
      and column_name = 'tenant_id'
      and table_name not in ('tenant_memberships', 'tenant_invites', 'tenant_audit_events')
  loop
    execute format(
      'alter table public.%I alter column tenant_id set default public.current_brain_tenant_id()',
      r.table_name
    );
  end loop;
end $$;

-- A constrained runtime role still needs ordinary SQL privileges before RLS can
-- enforce row visibility. Grant DML only to tenant-owned runtime tables. Tenant
-- lifecycle mutation remains unavailable until a durable administration service
-- and transactionally authoritative last-owner protection are implemented.
do $$
declare
  r record;
begin
  for r in
    select distinct table_name
    from information_schema.columns
    where table_schema = 'public'
      and column_name = 'tenant_id'
      and table_name not in (
        'tenant_memberships',
        'tenant_invites',
        'tenant_audit_events'
      )
  loop
    execute format(
      'grant select, insert, update, delete on table public.%I to brain_runtime_role',
      r.table_name
    );
  end loop;
end $$;

grant usage on schema public to brain_runtime_role;
grant usage, select on all sequences in schema public to brain_runtime_role;
grant select on table public.tenants, public.tenant_memberships to brain_runtime_role;
revoke insert, update, delete on table public.tenants, public.tenant_memberships
  from brain_runtime_role;
revoke all on table public.tenant_invites, public.tenant_audit_events
  from brain_runtime_role;

-- Cognitive Organism uses a constant checkpoint name, so the old global primary
-- key would prevent the same checkpoint name from existing in different tenants.
alter table public.cognitive_organism_checkpoints
  add column if not exists checkpoint_id uuid default gen_random_uuid();
update public.cognitive_organism_checkpoints
  set checkpoint_id = gen_random_uuid() where checkpoint_id is null;
alter table public.cognitive_organism_checkpoints
  alter column checkpoint_id set not null;
alter table public.cognitive_organism_checkpoints
  drop constraint if exists cognitive_organism_checkpoints_pkey;
alter table public.cognitive_organism_checkpoints
  add constraint cognitive_organism_checkpoints_pkey primary key (checkpoint_id);
create unique index if not exists cognitive_organism_checkpoints_system_name_unique_idx
  on public.cognitive_organism_checkpoints(checkpoint_name) where tenant_id is null;
create unique index if not exists cognitive_organism_checkpoints_tenant_name_unique_idx
  on public.cognitive_organism_checkpoints(tenant_id, checkpoint_name) where tenant_id is not null;

-- Generic cognitive object ids remain globally unique identities by design.
-- RLS controls visibility and tenant_id defaults stamp ownership. This avoids
-- conflating tenant-local display/natural keys with globally-addressable cognitive ids.
comment on table public.cognitive_objects is
  'Cognitive object identity is globally addressable; tenant ownership/visibility is enforced independently by tenant_id and RLS.';

comment on role brain_runtime_role is
  'NOLOGIN group for non-owner, non-BYPASSRLS Brain API/runtime logins. Membership is granted only by the gated migration runner after runtime-role verification.';
comment on role brain_trusted_service_role is
  'NOLOGIN audited service group used only by trusted cross-tenant internal workers. It inherits brain_runtime_role privileges and receives RLS service context solely through PostgreSQL role membership.';
