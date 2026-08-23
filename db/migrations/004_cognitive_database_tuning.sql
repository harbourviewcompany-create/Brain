create schema if not exists extensions;
alter extension vector set schema extensions;

create index if not exists belief_evidence_evidence_id_idx on public.belief_evidence(evidence_id);
create index if not exists cognitive_experiment_results_experiment_id_idx on public.cognitive_experiment_results(experiment_id);
create index if not exists evidence_observation_id_idx on public.evidence(observation_id);
create index if not exists graph_edges_source_id_idx on public.graph_edges(source_id);
create index if not exists graph_edges_target_id_idx on public.graph_edges(target_id);
create index if not exists observations_source_id_idx on public.observations(source_id);
create index if not exists outcomes_action_id_idx on public.outcomes(action_id);
