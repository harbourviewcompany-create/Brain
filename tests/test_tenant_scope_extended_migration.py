from pathlib import Path

MIGRATION = Path("db/migrations/021_tenant_scope_extended_cognition.sql")


def test_extended_tenant_scope_covers_post_pr3_runtime_tables():
    sql = MIGRATION.read_text()
    required = [
        "developmental_evidence_objects", "developmental_evidence_events",
        "self_state_snapshots", "goal_states", "global_workspace_items", "curiosity_tasks",
        "original_ideas", "dream_cycles", "agency_actions", "organism_audit_events",
        "global_workspace_frames", "workspace_items", "workspace_broadcasts",
        "cognitive_objects", "source_registry_sources", "source_registry_observations",
        "source_registry_signal_inbox", "cognitive_organism_checkpoints",
        "memory_system_records", "memory_consolidation_events", "memory_links",
        "memory_quarantine_decisions",
    ]
    for table in required:
        assert f"'{table}'" in sql
    assert "force row level security" in sql
    assert "tenant_id = public.current_brain_tenant_id()" in sql


def test_projection_checkpoint_identity_is_tenant_safe():
    sql = MIGRATION.read_text()
    assert "projection_checkpoints_pkey primary key (checkpoint_id)" in sql
    assert "projection_checkpoints_system_name_unique_idx" in sql
    assert "projection_checkpoints_tenant_name_unique_idx" in sql


def test_new_natural_keys_are_partitioned_by_tenant():
    sql = MIGRATION.read_text()
    for marker in [
        "global_workspace_frames_tenant_key_unique_idx",
        "memory_system_records_tenant_key_unique_idx",
        "memory_consolidation_events_tenant_key_unique_idx",
    ]:
        assert marker in sql
    assert "where tenant_id is null" in sql
    assert "where tenant_id is not null" in sql


def test_runtime_conflict_targets_are_deferred_atomically_not_silently():
    sql = MIGRATION.read_text()
    assert "migration 022 updates the adapter and conflict target atomically" in sql
    assert "cognitive_objects" in sql
    assert "cognitive_organism_checkpoints" in sql
