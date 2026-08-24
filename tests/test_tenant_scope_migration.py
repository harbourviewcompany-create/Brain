from pathlib import Path

MIGRATION = Path("db/migrations/013_tenant_scope_cognitive_tables.sql")


def _sql() -> str:
    return MIGRATION.read_text()


def test_migration_adds_tenant_context_helpers():
    sql = _sql()

    assert "current_brain_tenant_id" in sql
    assert "current_brain_actor_id" in sql
    assert "current_brain_service_context" in sql
    assert "brain.tenant_id" in sql
    assert "brain.actor_id" in sql
    assert "brain.service_context" in sql


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


def test_migration_creates_baseline_tenant_policies():
    sql = _sql()

    assert "tenant_isolation_select" in sql
    assert "tenant_isolation_insert" in sql
    assert "tenant_isolation_update" in sql
    assert "tenant_isolation_delete" in sql
    assert "tenant_id = public.current_brain_tenant_id()" in sql


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
