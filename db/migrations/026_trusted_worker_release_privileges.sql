-- Close the production tenant-release privilege gap for the trusted worker.
--
-- Migrations 019-025 establish the split API/worker role topology, tenant RLS,
-- durable connector runtime, and tenant-aware revenue persistence. Migration 024
-- is intentionally later than migration 022's blanket tenant-table grant pass,
-- so its connector tables never received ordinary SQL privileges for the
-- constrained trusted worker. The global money_lanes and revenue_source_scores
-- tables are also intentionally not tenant-owned, so they likewise sit outside
-- the brain_runtime_role grant sweep even though the worker revenue store uses
-- them as system-level state.
--
-- Keep the ordinary API/runtime role excluded. Only the audited trusted-service
-- role receives access, and global money state is protected by service-only RLS
-- policies derived from PostgreSQL role membership rather than request/GUC input.

revoke all on table
  public.source_connector_runtime_state,
  public.source_connector_ingestion_runs,
  public.source_connector_observations
from brain_runtime_role;

grant select, insert, update on table
  public.source_connector_runtime_state,
  public.source_connector_ingestion_runs,
  public.source_connector_observations
to brain_trusted_service_role;

alter table public.money_lanes enable row level security;
alter table public.revenue_source_scores enable row level security;

drop policy if exists trusted_service_system_money_lanes on public.money_lanes;
create policy trusted_service_system_money_lanes
on public.money_lanes
for all
to brain_trusted_service_role
using (public.current_brain_service_context())
with check (public.current_brain_service_context());

drop policy if exists trusted_service_system_revenue_source_scores
  on public.revenue_source_scores;
create policy trusted_service_system_revenue_source_scores
on public.revenue_source_scores
for all
to brain_trusted_service_role
using (public.current_brain_service_context())
with check (public.current_brain_service_context());

revoke all on table public.money_lanes from brain_runtime_role;
revoke all on table public.revenue_source_scores from brain_runtime_role;

grant select, insert, update on table public.money_lanes
  to brain_trusted_service_role;
grant select, insert, update on table public.revenue_source_scores
  to brain_trusted_service_role;

comment on policy trusted_service_system_money_lanes on public.money_lanes is
  'System/global money-lane state is available only to the audited trusted worker; ordinary tenant API runtimes remain excluded.';
comment on policy trusted_service_system_revenue_source_scores on public.revenue_source_scores is
  'System/global source reliability state is available only to the audited trusted worker; tenant runtimes reconstruct tenant learning from tenant-owned outcomes.';