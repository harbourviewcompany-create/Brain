from pathlib import Path


MIGRATION = Path("db/migrations/018_tenant_auth_foundation.sql")


def test_tenant_auth_migration_adds_required_foundation_tables():
    sql = MIGRATION.read_text()

    for table in [
        "tenants",
        "tenant_memberships",
        "tenant_invites",
        "tenant_audit_events",
    ]:
        assert f"create table if not exists {table}" in sql
        assert f"alter table {table} enable row level security" in sql


def test_tenant_auth_migration_does_not_store_plain_invite_tokens():
    sql = MIGRATION.read_text()

    assert "token_hash text not null unique" in sql
    assert "token text" not in sql


def test_tenant_auth_migration_does_not_retrofit_existing_cognitive_tables_in_pr2():
    sql = MIGRATION.read_text()

    assert "alter table beliefs add column tenant_id" not in sql
    assert "alter table brain_events add column tenant_id" not in sql
    assert "alter table outcomes add column tenant_id" not in sql
    assert "PR 3 owns tenant_id/RLS" in sql
