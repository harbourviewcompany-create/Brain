from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

import pytest

from brain.tenant_auth import TenantRole
from brain.tenant_context import TenantScopeViolation, trusted_tenant_context
from brain.tenant_runtime import (
    TenantIdentity,
    TenantPartitionedFactory,
    TenantRequestSecurity,
    TenantScopedConnectionPool,
    active_tenant_context,
    tenant_context_scope,
)


def _context(tenant: str, actor: str = "actor"):
    return trusted_tenant_context(
        tenant_id=UUID(tenant), actor_id=actor, roles=(TenantRole.OPERATOR,)
    )


def test_signed_tenant_context_is_verified_and_carries_no_header_roles():
    security = TenantRequestSecurity(mode="required", secret="secret", max_clock_skew_seconds=300)
    identity = TenantIdentity(
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        actor_id="user-1",
        timestamp=1000,
    )
    signature = security.sign(identity)
    context = security.parse_and_verify(
        {
            "X-Brain-Tenant-Id": str(identity.tenant_id),
            "X-Brain-Actor-Id": identity.actor_id,
            "X-Brain-Tenant-Timestamp": str(identity.timestamp),
            "X-Brain-Tenant-Signature": signature,
        },
        now=1000,
    )
    assert context is not None
    assert context.tenant_id == identity.tenant_id
    assert context.actor_id == "user-1"
    assert context.roles == ()


def test_tenant_signature_rejects_tamper_expiry_and_privilege_headers():
    security = TenantRequestSecurity(mode="required", secret="secret", max_clock_skew_seconds=60)
    identity = TenantIdentity(
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        actor_id="user-1",
        timestamp=1000,
    )
    signature = security.sign(identity)
    headers = {
        "x-brain-tenant-id": str(identity.tenant_id),
        "x-brain-actor-id": "user-2",
        "x-brain-tenant-timestamp": "1000",
        "x-brain-tenant-signature": signature,
    }
    with pytest.raises(TenantScopeViolation, match="invalid_tenant_context_signature"):
        security.parse_and_verify(headers, now=1000)

    headers["x-brain-actor-id"] = "user-1"
    with pytest.raises(TenantScopeViolation, match="tenant_context_signature_expired"):
        security.parse_and_verify(headers, now=2000)

    headers["x-brain-roles"] = "owner"
    with pytest.raises(TenantScopeViolation, match="verified membership"):
        security.parse_and_verify(headers, now=1000)


def test_partitioned_factory_never_shares_mutable_service_between_tenants():
    factory = TenantPartitionedFactory(list)
    one = _context("11111111-1111-1111-1111-111111111111")
    two = _context("22222222-2222-2222-2222-222222222222")
    with tenant_context_scope(one):
        factory.current().append("one")
    with tenant_context_scope(two):
        assert factory.current() == []
        factory.current().append("two")
    with tenant_context_scope(one):
        assert factory.current() == ["one"]


class _FakeConn:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return self


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    @contextmanager
    def connection(self, *args, **kwargs):
        yield self.conn


def test_scoped_pool_exports_only_tenant_and_actor_gucs():
    raw = _FakePool()
    pool = TenantScopedConnectionPool(raw)
    context = _context("11111111-1111-1111-1111-111111111111", "actor-1")
    with tenant_context_scope(context):
        with pool.connection():
            assert active_tenant_context() == context
    rendered = "\n".join(sql for sql, _ in raw.conn.calls)
    assert "brain.tenant_id" in rendered
    assert "brain.actor_id" in rendered
    assert "brain.service_context" not in rendered
