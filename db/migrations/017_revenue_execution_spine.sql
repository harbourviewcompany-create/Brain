-- Revenue Execution Spine V1 persistence.
-- Queues approved manual revenue actions. Does not send outreach, spend, or execute external actions.

create table if not exists revenue_execution_actions (
  id uuid primary key,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  opportunity_id uuid not null,
  offer_id uuid not null,
  lane_id text not null,
  source_id text not null,
  action_type text not null,
  target_contact text not null,
  proposal text not null,
  evidence_refs jsonb not null default '[]'::jsonb,
  approval_required boolean not null default true,
  state text not null,
  approved_by text,
  manual_proof_ref text
);

create table if not exists revenue_followups (
  id uuid primary key,
  action_id uuid not null references revenue_execution_actions(id),
  due_at timestamptz not null,
  script text not null,
  state text not null default 'scheduled',
  completed_at timestamptz
);

create table if not exists revenue_outcome_ledger (
  id uuid primary key,
  created_at timestamptz not null default now(),
  action_id uuid not null references revenue_execution_actions(id),
  lane_id text not null,
  source_id text not null,
  outcome_type text not null,
  revenue numeric not null default 0,
  reply boolean not null default false,
  meeting_booked boolean not null default false,
  paid_conversion boolean not null default false,
  legal_risk numeric not null default 0,
  operator_hours numeric not null default 0,
  lesson text not null
);

create index if not exists idx_revenue_execution_actions_state on revenue_execution_actions(state);
create index if not exists idx_revenue_followups_due on revenue_followups(state, due_at);
create index if not exists idx_revenue_outcome_ledger_lane_source on revenue_outcome_ledger(lane_id, source_id);

alter table revenue_execution_actions enable row level security;
alter table revenue_followups enable row level security;
alter table revenue_outcome_ledger enable row level security;

revoke all on revenue_execution_actions from public;
revoke all on revenue_followups from public;
revoke all on revenue_outcome_ledger from public;
