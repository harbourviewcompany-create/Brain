from pathlib import Path

MIGRATION = Path("db/migrations/021_tenant_runtime_enforcement.sql")


def test_membership_resolution_is_rls_scoped_to_signed_identity():
    sql = MIGRATION.read_text()
    assert "tenant_memberships force row level security" in sql
    assert "membership_self_select" in sql
    assert "user_id = public.current_brain_actor_id()" in sql
    assert "tenant_id = public.current_brain_tenant_id()" in sql


def test_runtime_tables_stamp_current_tenant_by_default():
    sql = MIGRATION.read_text()
    assert "alter column tenant_id set default public.current_brain_tenant_id()" in sql
    assert "information_schema.columns" in sql


def test_organism_checkpoint_name_is_tenant_partitioned():
    sql = MIGRATION.read_text()
    assert "cognitive_organism_checkpoints_pkey primary key (checkpoint_id)" in sql
    assert "cognitive_organism_checkpoints_system_name_unique_idx" in sql
    assert "cognitive_organism_checkpoints_tenant_name_unique_idx" in sql


def test_cognitive_object_identity_is_explicitly_global_but_visibility_is_tenant_scoped():
    sql = MIGRATION.read_text()
    assert "Cognitive object identity is globally addressable" in sql
    assert "tenant ownership/visibility is enforced independently" in sql
