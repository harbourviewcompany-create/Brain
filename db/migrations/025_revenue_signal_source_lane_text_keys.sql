-- Reconcile revenue scoring audit tables with the domain's stable text keys.
--
-- Migration 006 modeled revenue_signals.source_id, revenue_signals.money_lane_id,
-- and scored_revenue_opportunities.money_lane_id as UUID foreign keys. The domain
-- has always carried connector source keys and MoneyLane.lane_id strings instead.
-- Migration 017 already uses text keys for the execution ledger. This migration
-- brings the scoring audit trail onto the same contract.
--
-- Existing legacy UUID-backed rows are preserved semantically: after converting
-- the columns to text, UUID strings are translated to sources.key / money_lanes.lane_key
-- wherever they came from the old foreign keys. On an empty table the updates are
-- naturally no-ops. The statements are safe to replay after the conversion.

alter table revenue_signals
  drop constraint if exists revenue_signals_source_id_fkey,
  drop constraint if exists revenue_signals_money_lane_id_fkey;

alter table scored_revenue_opportunities
  drop constraint if exists scored_revenue_opportunities_money_lane_id_fkey;

alter table revenue_signals
  alter column source_id type text using source_id::text,
  alter column money_lane_id type text using money_lane_id::text;

alter table scored_revenue_opportunities
  alter column money_lane_id type text using money_lane_id::text;

-- Preserve any rows created under the UUID schema by translating the old
-- referenced IDs to the stable keys used by the runtime. On an idempotent replay,
-- already-converted keys simply do not match the UUID text and remain unchanged.
update revenue_signals rs
set source_id = s.key
from sources s
where rs.source_id = s.id::text;

update revenue_signals rs
set money_lane_id = ml.lane_key
from money_lanes ml
where rs.money_lane_id = ml.id::text;

update scored_revenue_opportunities sro
set money_lane_id = ml.lane_key
from money_lanes ml
where sro.money_lane_id = ml.id::text;

alter table revenue_signals
  alter column source_id set not null,
  alter column money_lane_id set not null;

alter table scored_revenue_opportunities
  alter column money_lane_id set not null;
