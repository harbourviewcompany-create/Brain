do $$
declare
  t text;
  role_name text;
begin
  foreach t in array array[
    'brain_events','sources','observations','evidence','entities','beliefs','belief_evidence',
    'graph_nodes','graph_edges','rewire_events','actions','outcomes','memory_items','bitemporal_facts',
    'neuromodulator_snapshots','homeostatic_snapshots','cognitive_tasks','cognitive_experiments',
    'cognitive_experiment_results','projection_checkpoints'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    foreach role_name in array array['anon','authenticated'] loop
      if exists (select 1 from pg_roles where rolname = role_name) then
        execute format('revoke all on table public.%I from %I', t, role_name);
      end if;
    end loop;
  end loop;
end $$;

do $$
declare
  sequence_name text;
  role_name text;
begin
  foreach sequence_name in array array[
    'neuromodulator_snapshots_id_seq',
    'homeostatic_snapshots_id_seq',
    'cognitive_experiment_results_id_seq'
  ] loop
    foreach role_name in array array['anon','authenticated'] loop
      if exists (select 1 from pg_roles where rolname = role_name) then
        execute format('revoke all on sequence public.%I from %I', sequence_name, role_name);
      end if;
    end loop;
  end loop;
end $$;

create or replace function public.prevent_brain_event_mutation()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  raise exception 'brain_events is append-only';
end;
$$;

revoke all on function public.prevent_brain_event_mutation() from public;

do $$
declare
  role_name text;
begin
  foreach role_name in array array['anon','authenticated'] loop
    if exists (select 1 from pg_roles where rolname = role_name) then
      execute format(
        'revoke all on function public.prevent_brain_event_mutation() from %I',
        role_name
      );
    end if;
  end loop;
end $$;

drop trigger if exists brain_events_append_only_update on public.brain_events;
create trigger brain_events_append_only_update
before update on public.brain_events
for each row execute function public.prevent_brain_event_mutation();

drop trigger if exists brain_events_append_only_delete on public.brain_events;
create trigger brain_events_append_only_delete
before delete on public.brain_events
for each row execute function public.prevent_brain_event_mutation();
