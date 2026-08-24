-- Cognitive Organism Layer V1 persistence.
-- Functional consciousness proxy only. No claim of subjective consciousness.

create table if not exists self_state_snapshots (
  id uuid primary key,
  created_at timestamptz not null default now(),
  development_stage text not null,
  current_focus_summary text not null,
  active_goal_ids jsonb not null default '[]'::jsonb,
  active_workspace_item_ids jsonb not null default '[]'::jsonb,
  belief_count integer not null default 0,
  event_count integer not null default 0,
  prediction_count integer not null default 0,
  opportunity_count integer not null default 0,
  uncertainty_load numeric not null default 0,
  contradiction_load numeric not null default 0,
  curiosity_pressure numeric not null default 0,
  revenue_pressure numeric not null default 0,
  risk_pressure numeric not null default 0,
  memory_pressure numeric not null default 0,
  action_backlog_pressure numeric not null default 0,
  self_assessment text not null,
  changed_since_last_snapshot boolean not null default false,
  source_event_ids jsonb not null default '[]'::jsonb,
  phase text not null,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists goal_states (
  id uuid primary key,
  goal_name text not null,
  goal_type text not null,
  target numeric not null,
  current numeric not null,
  pressure numeric not null,
  priority numeric not null,
  state text not null,
  evidence_refs jsonb not null default '[]'::jsonb,
  last_updated_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists goal_pressure_events (
  id uuid primary key,
  goal_id uuid not null,
  from_state text not null,
  to_state text not null,
  reason text not null,
  pressure numeric not null,
  created_at timestamptz not null default now()
);

create table if not exists global_workspace_items (
  id uuid primary key,
  item_type text not null,
  title text not null,
  content text not null,
  source_refs jsonb not null default '[]'::jsonb,
  salience numeric not null,
  novelty numeric not null default 0,
  urgency numeric not null default 0,
  risk numeric not null default 0,
  goal_pressure numeric not null default 0,
  admission_reason text not null default '',
  state text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists workspace_focus_history (
  id uuid primary key,
  item_id uuid not null,
  from_state text not null,
  to_state text not null,
  reason text not null,
  created_at timestamptz not null default now()
);

create table if not exists curiosity_tasks (
  id uuid primary key,
  question text not null,
  trigger_type text not null,
  trigger_refs jsonb not null default '[]'::jsonb,
  expected_uncertainty_reduction numeric not null,
  expected_value numeric not null,
  research_cost numeric not null,
  priority numeric not null,
  state text not null,
  falsification_condition text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists imagination_runs (
  id uuid primary key,
  created_at timestamptz not null default now(),
  seed_refs jsonb not null default '[]'::jsonb,
  combination_method text not null,
  candidate_idea text not null,
  recombination_notes jsonb not null default '[]'::jsonb
);

create table if not exists original_ideas (
  id uuid primary key,
  created_at timestamptz not null default now(),
  title text not null,
  idea text not null,
  source_signal_refs jsonb not null default '[]'::jsonb,
  memory_refs jsonb not null default '[]'::jsonb,
  combination_method text not null,
  novelty_score numeric not null,
  non_obviousness_score numeric not null,
  revenue_path_score numeric not null,
  speed_to_test_score numeric not null,
  risk_score numeric not null,
  spawn_potential text not null,
  why_most_people_miss_it text not null,
  fastest_test text not null,
  kill_condition text not null,
  skeptic_objections jsonb not null default '[]'::jsonb,
  approval_status text not null,
  state text not null,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists dream_cycles (
  id uuid primary key,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  input_memory_refs jsonb not null default '[]'::jsonb,
  input_signal_refs jsonb not null default '[]'::jsonb,
  compression_summary text not null,
  state text not null,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists dream_insights (
  id uuid primary key,
  dream_cycle_id uuid not null,
  created_at timestamptz not null default now(),
  insight text not null,
  pattern text not null,
  priority_change jsonb not null default '{}'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  confidence numeric not null,
  requires_review boolean not null default true
);

create table if not exists internal_debates (
  id uuid primary key,
  proposal_type text not null,
  proposal_ref text,
  topic text not null,
  verdict text not null,
  confidence numeric not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists debate_arguments (
  id uuid primary key,
  debate_id uuid not null,
  role text not null,
  stance text not null,
  argument text not null,
  evidence_refs jsonb not null default '[]'::jsonb,
  confidence numeric not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists immune_quarantine_items (
  id uuid primary key,
  item_type text not null,
  item_ref text not null,
  reason text not null,
  severity numeric not null,
  state text not null,
  evidence_refs jsonb not null default '[]'::jsonb,
  review_required boolean not null default true,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists agency_policies (
  id uuid primary key,
  policy_name text not null,
  allowed_tiers jsonb not null default '[]'::jsonb,
  prohibited_actions jsonb not null default '[]'::jsonb,
  requires_approval_actions jsonb not null default '[]'::jsonb,
  risk_threshold numeric not null default 0.65,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists agency_actions (
  id uuid primary key,
  action_type text not null,
  tier text not null,
  proposal text not null,
  source_refs jsonb not null default '[]'::jsonb,
  workspace_item_id uuid,
  debate_id uuid,
  policy_id uuid not null,
  approval_status text not null,
  approved_by text,
  executed_at timestamptz,
  outcome_ref text,
  state text not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists development_events (
  id uuid primary key,
  event_type text not null,
  before_snapshot_id uuid,
  after_snapshot_id uuid not null,
  change_summary text not null,
  cause_refs jsonb not null default '[]'::jsonb,
  priority_deltas jsonb not null default '{}'::jsonb,
  belief_deltas jsonb not null default '{}'::jsonb,
  source_score_deltas jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists organism_audit_events (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  event_type text not null,
  object_type text not null,
  object_id text not null,
  payload jsonb not null default '{}'::jsonb
);

alter table self_state_snapshots enable row level security;
alter table goal_states enable row level security;
alter table global_workspace_items enable row level security;
alter table curiosity_tasks enable row level security;
alter table original_ideas enable row level security;
alter table dream_cycles enable row level security;
alter table dream_insights enable row level security;
alter table internal_debates enable row level security;
alter table immune_quarantine_items enable row level security;
alter table agency_actions enable row level security;
alter table development_events enable row level security;

revoke all on self_state_snapshots from public;
revoke all on goal_states from public;
revoke all on global_workspace_items from public;
revoke all on curiosity_tasks from public;
revoke all on original_ideas from public;
revoke all on dream_cycles from public;
revoke all on dream_insights from public;
revoke all on internal_debates from public;
revoke all on immune_quarantine_items from public;
revoke all on agency_actions from public;
revoke all on development_events from public;
