-- revenue_signals.source_id and revenue_signals.money_lane_id were
-- originally declared as uuid foreign keys (into sources(id) and
-- money_lanes(id) respectively), but the domain code
-- (MoneySpineService, RevenueSignal, the connector layer) has always
-- addressed both by their string keys — source_id as the connector's
-- source_key (e.g. "who-ecdd-rss"), money_lane_id as the lane's
-- lane_id/lane_key (e.g. "procurement_rfp_match") — never by either
-- table's internal uuid primary key.
--
-- Migration 017 (revenue_execution_spine) already got this right:
-- revenue_execution_actions.source_id and .lane_id are both
-- `text not null`, no FK. This migration brings revenue_signals in
-- line with that, so brain/adapters/revenue_store.py can persist
-- RevenueSignal/ScoredOpportunity/PackagedOffer without either
-- violating a foreign key or silently resolving a string key to a
-- uuid at every write. Flagged as an unresolved gap in #164's
-- TRACE-REVENUE-EXECUTION-PERSISTENCE record; this closes it.
--
-- No deployed code path has ever written to revenue_signals (see
-- #164 / #171's discussion of why persistence for this table was
-- deferred), so this is a schema-only alteration with no data to
-- migrate.

alter table revenue_signals
  drop constraint if exists revenue_signals_source_id_fkey,
  drop constraint if exists revenue_signals_money_lane_id_fkey;

alter table revenue_signals
  alter column source_id type text using source_id::text,
  alter column money_lane_id type text using money_lane_id::text;

alter table revenue_signals
  alter column source_id set not null,
  alter column money_lane_id set not null;
