-- Reconcile revenue scoring audit tables with the domain's stable text keys.
--
-- Migration 006 modeled revenue_signals.source_id, revenue_signals.money_lane_id,
-- and scored_revenue_opportunities.money_lane_id as UUID foreign keys. The domain
-- carries connector source keys and MoneyLane.lane_id / money_lanes.lane_key strings.
-- Migration 017 already uses text keys for the execution ledger. This migration
-- brings the scoring audit trail onto the same stable-key contract.
--
-- Existing legacy UUID-backed rows are preserved semantically: after converting
-- the columns to text, non-null UUID strings are translated to sources.key /
-- money_lanes.lane_key wherever they came from the old foreign keys. Migration 006
-- intentionally allowed these key columns to be null, so this migration preserves
-- that nullability instead of inventing a destructive/backfill policy for legacy nulls.
--
-- Migrations 020-022 FORCE RLS on sources and the tenant-owned revenue audit tables.
-- The migration runner executes each migration transactionally as the schema
-- migrator/table owner. Temporarily removing FORCE (while leaving RLS enabled) lets
-- that owner translate pre-tenant system rows whose tenant_id is null; FORCE is
-- restored before this transaction commits. Other roles remain subject to RLS.

alter table public.sources no force row level security;
alter table public.revenue_signals no force row level security;
alter table public.scored_revenue_opportunities no force row level security;

alter table public.revenue_signals
  drop constraint if exists revenue_signals_source_id_fkey,
  drop constraint if exists revenue_signals_money_lane_id_fkey;

alter table public.scored_revenue_opportunities
  drop constraint if exists scored_revenue_opportunities_money_lane_id_fkey;

alter table public.revenue_signals
  alter column source_id type text using source_id::text,
  alter column money_lane_id type text using money_lane_id::text;

alter table public.scored_revenue_opportunities
  alter column money_lane_id type text using money_lane_id::text;

-- Preserve rows created under the UUID schema by translating old referenced IDs to
-- stable runtime keys. Nulls remain null. On replay, already-converted keys simply do
-- not match UUID ids and therefore remain unchanged.
update public.revenue_signals rs
set source_id = s.key
from public.sources s
where rs.source_id is not null
  and rs.source_id = s.id::text;

update public.revenue_signals rs
set money_lane_id = ml.lane_key
from public.money_lanes ml
where rs.money_lane_id is not null
  and rs.money_lane_id = ml.id::text;

update public.scored_revenue_opportunities sro
set money_lane_id = ml.lane_key
from public.money_lanes ml
where sro.money_lane_id is not null
  and sro.money_lane_id = ml.id::text;

alter table public.sources force row level security;
alter table public.revenue_signals force row level security;
alter table public.scored_revenue_opportunities force row level security;
