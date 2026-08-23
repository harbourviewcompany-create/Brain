do $$
declare
  t text;
begin
  foreach t in array array[
    'brain_events','sources','observations','evidence','entities','beliefs','belief_evidence',
    'graph_nodes','graph_edges','rewire_events','actions','outcomes','memory_items','bitemporal_facts',
    'neuromodulator_snapshots','homeostatic_snapshots','cognitive_tasks','cognitive_experiments',
    'cognitive_experiment_results','projection_checkpoints'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on table public.%I from anon, authenticated', t);
  end loop;
end $$;

revoke all on sequence public.neuromodulator_snapshots_id_seq from anon, authenticated;
revoke all on sequence public.homeostatic_snapshots_id_seq from anon, authenticated;
revoke all on sequence public.cognitive_experiment_results_id_seq from anon, authenticated;

create or replace function public.prevent_brain_event_mutation()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  raise exception 'brain_events is append-only';
end;
$$;

revoke all on function public.prevent_brain_event_mutation() from public, anon, authenticated;

drop trigger if exists brain_events_append_only_update on public.brain_events;
create trigger brain_events_append_only_update
before update on public.brain_events
for each row execute function public.prevent_brain_event_mutation();

drop trigger if exists brain_events_append_only_delete on public.brain_events;
create trigger brain_events_append_only_delete
before delete on public.brain_events
for each row execute function public.prevent_brain_event_mutation();
