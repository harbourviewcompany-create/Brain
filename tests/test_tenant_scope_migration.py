from pathlib import Path

MIGRATION = Path("db/migrations/013_tenant_scope_cognitive_tables.sql")


def _sql() -> str:
    return MIGRATION.read_text()


def test_migration_adds_tenant_context_helpers_without_user_settable_service_guc():
    sql = _sql()

    assert "current_brain_tenant_id" in sql
    assert "current_brain_actor_id" in sql
    assert "current_brain_service_context" in sql
    assert "brain.tenant_id" in sql
    assert "brain.actor_id" in sql
    assert "brain.service_context" not in sql
    assert "pg_has_role(current_user, 'brain_trusted_service_role', 'member')" in sql


def test_migration_adds_tenant_id_to_existing_cognitive_tables():
    sql = _sql()
    required_tables = [
        "brain_events",
        "sources",
        "observations",
        "evidence",
        "entities",
        "beliefs",
        "belief_evidence",
        "graph_nodes",
        "graph_edges",
        "rewire_events",
        "actions",
        "outcomes",
        "memory_items",
        "bitemporal_facts",
        "neuromodulator_snapshots",
        "homeostatic_snapshots",
        "cognitive_tasks",
        "cognitive_experiments",
        "cognitive_experiment_results",
        "projection_checkpoints",
        "sensory_inbox",
        "cognitive_cycle_runs",
        "predictions",
        "attribution_records",
        "working_memory_snapshots",
        "revenue_signals",
        "scored_revenue_opportunities",
        "packaged_offers",
        "revenue_experiments",
        "revenue_experiment_results",
        "daily_revenue_reports",
        "economic_objects",
        "economic_transitions",
        "economic_formula_runs",
    ]

    assert "add column if not exists tenant_id uuid references public.tenants" in sql
    for table in required_tables:
        assert f"'{table}'" in sql


def test_migration_creates_baseline_tenant_policies_and_forces_rls():
    sql = _sql()

    assert "tenant_isolation_select" in sql
    assert "tenant_isolation_insert" in sql
    assert "tenant_isolation_update" in sql
    assert "tenant_isolation_delete" in sql
    assert "tenant_id = public.current_brain_tenant_id()" in sql
    assert "force row level security" in sql


def test_migration_remains_additive_for_legacy_rows():
    sql = _sql().lower()

    assert "tenant_id uuid references public.tenants" in sql
    assert "tenant_id uuid not null" not in sql
    assert "legacy/global rows are backfilled" in sql


def test_migration_preserves_explicit_deferred_system_registries():
    sql = _sql()

    assert "money_lanes" in sql
    assert "global/system-defined" in sql
    assert "neuro_abstractions" in sql
    assert "system control registry" in sql


def test_migration_makes_safe_natural_uniqueness_tenant_scoped():
    sql = _sql()

    assert "sources_tenant_key_unique_idx" in sql
    assert "entities_tenant_kind_key_unique_idx" in sql
    assert "graph_nodes_tenant_kind_key_unique_idx" in sql
    assert "daily_revenue_reports_tenant_date_unique_idx" in sql
    assert "where tenant_id is not null" in sql
    assert "where tenant_id is null" in sql


def test_migration_documents_remaining_projection_uniqueness_blocker():
    sql = _sql()

    assert "projection_name primary key remains" in sql
    assert "tenant-breaking uniqueness constraint" in sql


def test_migration_documents_runtime_role_requirement():
    sql = _sql()

    assert "non-owner, non-BYPASSRLS role" in sql
    assert "brain_trusted_service_role" in sql
    assert "No request header or custom" in sql
