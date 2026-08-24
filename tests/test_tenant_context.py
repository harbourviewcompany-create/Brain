from uuid import uuid4

import pytest

from brain.tenant_auth import TenantRole
from brain.tenant_context import (
    TenantContext,
    TenantScopeViolation,
    parse_tenant_context_headers,
    trusted_tenant_context,
)


def test_tenant_context_requires_same_tenant():
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    context = TenantContext(
        tenant_id=tenant_id,
        actor_id="user-1",
        roles=(TenantRole.OWNER,),
    )

    context.require_same_tenant(tenant_id)
    with pytest.raises(TenantScopeViolation, match="cross_tenant_access_denied"):
        context.require_same_tenant(other_tenant_id)


def test_tenant_context_role_check_blocks_missing_role():
    context = TenantContext(
        tenant_id=uuid4(),
        actor_id="operator-1",
        roles=(TenantRole.OPERATOR,),
    )

    context.require_role(TenantRole.OPERATOR)
    with pytest.raises(TenantScopeViolation):
        context.require_role(TenantRole.OWNER, TenantRole.ADMIN)


def test_trusted_service_context_can_pass_role_checks_but_keeps_tenant_identity():
    tenant_id = uuid4()
    context = trusted_tenant_context(
        tenant_id=tenant_id,
        actor_id="service:cognition",
        roles=(),
        service_context=True,
    )

    context.require_role(TenantRole.OWNER)
    assert context.sql_settings["brain.tenant_id"] == str(tenant_id)
    assert "brain.service_context" not in context.sql_settings


def test_parse_tenant_context_headers_returns_none_when_absent():
    assert parse_tenant_context_headers({}) is None


def test_parse_tenant_context_headers_requires_tenant_and_actor_together():
    with pytest.raises(TenantScopeViolation):
        parse_tenant_context_headers({"x-brain-tenant-id": str(uuid4())})


def test_parse_tenant_context_headers_builds_identity_context_without_roles():
    tenant_id = uuid4()
    context = parse_tenant_context_headers(
        {
            "x-brain-tenant-id": str(tenant_id),
            "x-brain-actor-id": "user-1",
        }
    )

    assert context is not None
    assert context.tenant_id == tenant_id
    assert context.actor_id == "user-1"
    assert context.roles == ()
    assert context.service_context is False


def test_parse_tenant_context_headers_rejects_untrusted_roles():
    with pytest.raises(TenantScopeViolation, match="verified membership"):
        parse_tenant_context_headers(
            {
                "x-brain-tenant-id": str(uuid4()),
                "x-brain-actor-id": "user-1",
                "x-brain-roles": "owner",
            }
        )


def test_parse_tenant_context_headers_rejects_untrusted_service_context():
    with pytest.raises(TenantScopeViolation, match="service context"):
        parse_tenant_context_headers(
            {
                "x-brain-tenant-id": str(uuid4()),
                "x-brain-actor-id": "service:cognition",
                "x-brain-service-context": "true",
            }
        )


def test_parse_tenant_context_headers_converts_malformed_tenant_id_to_scope_violation():
    with pytest.raises(TenantScopeViolation, match="invalid_tenant_id"):
        parse_tenant_context_headers(
            {
                "x-brain-tenant-id": "not-a-uuid",
                "x-brain-actor-id": "user-1",
            }
        )


def test_trusted_tenant_context_requires_actor_identity():
    with pytest.raises(TenantScopeViolation, match="actor identity"):
        trusted_tenant_context(tenant_id=uuid4(), actor_id="", roles=(TenantRole.OWNER,))
