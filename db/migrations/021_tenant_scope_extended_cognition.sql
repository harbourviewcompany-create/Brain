-- Brain tenant scope extension for persistence added after the original PR 3 baseline.
-- Depends on migrations 019_tenant_auth_foundation.sql and 020_tenant_scope_cognitive_tables.sql.
-- System neuroscience registries remain global control surfaces; runtime cognition is tenant-scoped.

do $$
declare
  t text;
begin
  foreach t in array array[
    'developmental_evidence_objects',
    'developmental_evidence_events',
    'self_state_snapshots',
    'goal_states',
    'goal_pressure_events',
    'global_workspace_items',
    'workspace_focus_history',
    'curiosity_tasks',
    'imagination_runs',
    'original_ideas',
    'dream_cycles',
    'dream_insights',
    'internal_debates',
    'debate_arguments',
    'immune_quarantine_items',
    'agency_policies',
    'agency_actions',
    'development_events',
    'organism_audit_events',
    'global_workspace_frames',
    'workspace_items',
    'workspace_broadcasts',
    'workspace_access_decisions',
    'cognitive_objects',
    'source_registry_sources',
    'source_registry_ingestion_runs',
    'source_registry_observations',
    'source_registry_signal_inbox',
    'source_registry_health_checks',
    'source_registry_events',
    'cognitive_organism_checkpoints',
    'memory_system_records',
    'memory_consolidation_events',
    'memory_links',
    'memory_quarantine_decisions'
  ] loop
    if to_regclass(format('public.%I', t)) is null then
      raise exception 'tenant scope extension requires missing table public.%', t;
    end if;

    execute format(
      'alter table public.%I add column if not exists tenant_id uuid references public.tenants(id) on delete restrict',
      t
    );
    execute format('create index if not exists %I on public.%I (tenant_id)', t || '_tenant_id_idx', t);
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);

    execute format('drop policy if exists tenant_isolation_select on public.%I', t);
    execute format(
      'create policy tenant_isolation_select on public.%I for select using (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists tenant_isolation_insert on public.%I', t);
    execute format(
      'create policy tenant_isolation_insert on public.%I for insert with check (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists tenant_isolation_update on public.%I', t);
    execute format(
      'create policy tenant_isolation_update on public.%I for update using (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context()) with check (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );
    execute format('drop policy if exists tenant_isolation_delete on public.%I', t);
    execute format(
      'create policy tenant_isolation_delete on public.%I for delete using (tenant_id = public.current_brain_tenant_id() or public.current_brain_service_context())',
      t
    );
  end loop;
end $$;

-- Fix the explicit PR 3 projection checkpoint blocker without requiring legacy backfill.
alter table public.projection_checkpoints add column if not exists checkpoint_id uuid default gen_random_uuid();
update public.projection_checkpoints set checkpoint_id = gen_random_uuid() where checkpoint_id is null;
alter table public.projection_checkpoints alter column checkpoint_id set not null;
alter table public.projection_checkpoints drop constraint if exists projection_checkpoints_pkey;
alter table public.projection_checkpoints add constraint projection_checkpoints_pkey primary key (checkpoint_id);
create unique index if not exists projection_checkpoints_system_name_unique_idx
  on public.projection_checkpoints(projection_name) where tenant_id is null;
create unique index if not exists projection_checkpoints_tenant_name_unique_idx
  on public.projection_checkpoints(tenant_id, projection_name) where tenant_id is not null;

-- Natural keys introduced after PR 3 become tenant-aware while retaining legacy/system rows.
alter table public.global_workspace_frames drop constraint if exists global_workspace_frames_frame_key_key;
create unique index if not exists global_workspace_frames_system_key_unique_idx
  on public.global_workspace_frames(frame_key) where tenant_id is null;
create unique index if not exists global_workspace_frames_tenant_key_unique_idx
  on public.global_workspace_frames(tenant_id, frame_key) where tenant_id is not null;

alter table public.memory_system_records drop constraint if exists memory_system_records_memory_key_key;
create unique index if not exists memory_system_records_system_key_unique_idx
  on public.memory_system_records(memory_key) where tenant_id is null;
create unique index if not exists memory_system_records_tenant_key_unique_idx
  on public.memory_system_records(tenant_id, memory_key) where tenant_id is not null;

alter table public.memory_consolidation_events drop constraint if exists memory_consolidation_events_event_key_key;
create unique index if not exists memory_consolidation_events_system_key_unique_idx
  on public.memory_consolidation_events(event_key) where tenant_id is null;
create unique index if not exists memory_consolidation_events_tenant_key_unique_idx
  on public.memory_consolidation_events(tenant_id, event_key) where tenant_id is not null;

-- These two runtime stores still use their historical natural keys as conflict targets.
-- Migration 022 changes them atomically with their adapters so no application build can
-- observe a schema/runtime mismatch.
comment on table public.cognitive_objects is
  'Tenant-scoped by RLS in migration 021. Global (object_id, kind) key is retained only until migration 022 updates the adapter and conflict target atomically.';
comment on table public.cognitive_organism_checkpoints is
  'Tenant-scoped by RLS in migration 021. Global checkpoint_name key is retained only until migration 022 updates the adapter and conflict target atomically.';
