-- Brain PR #126 release integration: preserve pre-tenant production state under FORCE RLS.
--
-- Migrations 020-022 deliberately leave historical tenant_id values nullable,
-- but an ordinary non-owner/NOBYPASSRLS runtime cannot read or write those rows
-- without a verified tenant context. The existing production Brain database is
-- a single pre-tenant installation, so this migration assigns existing rows in
-- the explicitly tenant-owned 020/021 schema to one deterministic compatibility
-- tenant and creates the durable Observatory service membership used by the
-- authenticated Vercel deployment-identity bridge.
--
-- This is a one-time ownership assignment for rows that exist when the migration
-- runs. It does not make tenant_id NOT NULL and therefore does not remove the
-- explicitly supported system/global-row model for future controlled use.

insert into public.tenants (
  id,
  name,
  slug,
  status
) values (
  '7d4427c4-8b8d-4f4a-9f75-b46cedc2f126'::uuid,
  'Brain Observatory Legacy Production',
  'brain-observatory-legacy-production',
  'active'
)
on conflict (id) do nothing;

insert into public.tenant_memberships (
  tenant_id,
  user_id,
  role,
  status
) values (
  '7d4427c4-8b8d-4f4a-9f75-b46cedc2f126'::uuid,
  'brain-observatory-bff',
  'operator',
  'active'
)
on conflict (tenant_id, user_id) do nothing;

do $$
declare
  compatibility_tenant constant uuid := '7d4427c4-8b8d-4f4a-9f75-b46cedc2f126'::uuid;
  existing_slug_tenant uuid;
  observatory_role text;
  observatory_status text;
  r record;
begin
  select id into existing_slug_tenant
  from public.tenants
  where slug = 'brain-observatory-legacy-production';

  if existing_slug_tenant is distinct from compatibility_tenant then
    raise exception
      'legacy Observatory tenant slug already belongs to a different tenant';
  end if;

  select role, status into observatory_role, observatory_status
  from public.tenant_memberships
  where tenant_id = compatibility_tenant
    and user_id = 'brain-observatory-bff';

  if observatory_role is distinct from 'operator'
     or observatory_status is distinct from 'active' then
    raise exception
      'legacy Observatory service membership conflicts with required active operator role';
  end if;

  -- The only tables considered here are those that already have tenant_id at
  -- this point in the canonical migration order (020/021/022). Auth/control
  -- metadata is excluded because its ownership is semantically explicit.
  -- brain_events is handled separately because its append-only trigger must
  -- remain authoritative outside this one transactional ownership migration.
  for r in
    select c.table_name
    from information_schema.columns c
    where c.table_schema = 'public'
      and c.column_name = 'tenant_id'
      and c.table_name not in (
        'brain_events',
        'tenant_memberships',
        'tenant_invites',
        'tenant_audit_events'
      )
    order by c.table_name
  loop
    execute format(
      'update public.%I set tenant_id = $1 where tenant_id is null',
      r.table_name
    ) using compatibility_tenant;
  end loop;
end $$;

-- brain_events is append-only in normal operation. PostgreSQL DDL is
-- transactional, so this narrowly scoped trigger suspension cannot commit in a
-- disabled state if the tenant assignment fails. No event payload, identity, or
-- timestamp is changed.
alter table public.brain_events disable trigger brain_events_append_only_update;
update public.brain_events
set tenant_id = '7d4427c4-8b8d-4f4a-9f75-b46cedc2f126'::uuid
where tenant_id is null;
alter table public.brain_events enable trigger brain_events_append_only_update;

comment on table public.tenants is
  'Tenant lifecycle root. The deterministic brain-observatory-legacy-production tenant preserves ownership of pre-tenant production state after migrations 020-022.';
