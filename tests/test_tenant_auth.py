from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from brain.tenant_auth import (
    InMemoryTenantAuthStore,
    InviteStatus,
    MembershipStatus,
    TenantAuthError,
    TenantAuthService,
    TenantRole,
    TenantStatus,
)


def _service() -> TenantAuthService:
    return TenantAuthService(InMemoryTenantAuthStore())


def test_create_tenant_creates_active_tenant_owner_membership_and_audit_events():
    service = _service()

    tenant = service.create_tenant(name="Harbourview Brain", owner_user_id="owner-1")

    assert tenant.status == TenantStatus.ACTIVE
    assert tenant.slug == "harbourview-brain"
    membership = service.require_membership(tenant_id=tenant.id, user_id="owner-1")
    assert membership.role == TenantRole.OWNER
    assert membership.status == MembershipStatus.ACTIVE
    assert [event.event_type for event in service.store.audit_events] == [
        "tenant.created",
        "membership.owner_created",
    ]


def test_require_membership_rejects_non_member():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")

    with pytest.raises(TenantAuthError) as exc:
        service.require_membership(tenant_id=tenant.id, user_id="stranger")

    assert exc.value.code == "membership_not_found"


def test_admin_can_invite_operator_and_operator_can_accept():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")
    admin_invite = service.create_invite(
        tenant_id=tenant.id,
        email="admin@example.com",
        role=TenantRole.ADMIN,
        invited_by_user_id="owner-1",
        token="admin-token",
    )
    admin_membership = service.accept_invite(token=admin_invite.token, accepted_by_user_id="admin-1")
    assert admin_membership.role == TenantRole.ADMIN

    operator_invite = service.create_invite(
        tenant_id=tenant.id,
        email="operator@example.com",
        role=TenantRole.OPERATOR,
        invited_by_user_id="admin-1",
        token="operator-token",
    )
    operator_membership = service.accept_invite(
        token=operator_invite.token,
        accepted_by_user_id="operator-1",
    )

    assert operator_membership.role == TenantRole.OPERATOR
    assert service.store.invites[operator_invite.token].status == InviteStatus.ACCEPTED


def test_operator_cannot_invite_members():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")
    operator_invite = service.create_invite(
        tenant_id=tenant.id,
        email="operator@example.com",
        role=TenantRole.OPERATOR,
        invited_by_user_id="owner-1",
        token="operator-token",
    )
    service.accept_invite(token=operator_invite.token, accepted_by_user_id="operator-1")

    with pytest.raises(TenantAuthError) as exc:
        service.create_invite(
            tenant_id=tenant.id,
            email="viewer@example.com",
            role=TenantRole.VIEWER,
            invited_by_user_id="operator-1",
        )

    assert exc.value.code == "role_forbidden"


def test_admin_cannot_invite_owner():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")
    admin_invite = service.create_invite(
        tenant_id=tenant.id,
        email="admin@example.com",
        role=TenantRole.ADMIN,
        invited_by_user_id="owner-1",
        token="admin-token",
    )
    service.accept_invite(token=admin_invite.token, accepted_by_user_id="admin-1")

    with pytest.raises(TenantAuthError) as exc:
        service.create_invite(
            tenant_id=tenant.id,
            email="new-owner@example.com",
            role=TenantRole.OWNER,
            invited_by_user_id="admin-1",
        )

    assert exc.value.code == "owner_invite_requires_owner"


def test_expired_invite_is_marked_expired_and_rejected():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")
    now = datetime.now(UTC)
    invite = service.create_invite(
        tenant_id=tenant.id,
        email="expired@example.com",
        role=TenantRole.VIEWER,
        invited_by_user_id="owner-1",
        token="expired-token",
        expires_at=now - timedelta(seconds=1),
    )

    with pytest.raises(TenantAuthError) as exc:
        service.accept_invite(token=invite.token, accepted_by_user_id="viewer-1", now=now)

    assert exc.value.code == "invite_expired"
    assert service.store.invites[invite.token].status == InviteStatus.EXPIRED


def test_revoke_invite_prevents_acceptance():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")
    invite = service.create_invite(
        tenant_id=tenant.id,
        email="viewer@example.com",
        role=TenantRole.VIEWER,
        invited_by_user_id="owner-1",
        token="viewer-token",
    )

    revoked = service.revoke_invite(
        tenant_id=tenant.id,
        token=invite.token,
        actor_user_id="owner-1",
    )

    assert revoked.status == InviteStatus.REVOKED
    with pytest.raises(TenantAuthError) as exc:
        service.accept_invite(token=invite.token, accepted_by_user_id="viewer-1")
    assert exc.value.code == "invite_not_pending"


def test_cannot_remove_last_owner():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")

    with pytest.raises(TenantAuthError) as exc:
        service.remove_member(
            tenant_id=tenant.id,
            target_user_id="owner-1",
            actor_user_id="owner-1",
        )

    assert exc.value.code == "cannot_remove_last_owner"


def test_cannot_demote_last_owner():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")

    with pytest.raises(TenantAuthError) as exc:
        service.change_member_role(
            tenant_id=tenant.id,
            target_user_id="owner-1",
            new_role=TenantRole.ADMIN,
            actor_user_id="owner-1",
        )

    assert exc.value.code == "cannot_remove_last_owner"


def test_owner_can_promote_second_owner_then_demote_first_owner():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")
    invite = service.create_invite(
        tenant_id=tenant.id,
        email="owner2@example.com",
        role=TenantRole.OWNER,
        invited_by_user_id="owner-1",
        token="owner2-token",
    )
    service.accept_invite(token=invite.token, accepted_by_user_id="owner-2")

    updated = service.change_member_role(
        tenant_id=tenant.id,
        target_user_id="owner-1",
        new_role=TenantRole.ADMIN,
        actor_user_id="owner-2",
    )

    assert updated.role == TenantRole.ADMIN


def test_suspended_tenant_blocks_membership_authorization():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")

    updated = service.set_tenant_status(
        tenant_id=tenant.id,
        status=TenantStatus.SUSPENDED,
        actor_user_id="owner-1",
        reason="billing_hold",
    )

    assert updated.status == TenantStatus.SUSPENDED
    with pytest.raises(TenantAuthError) as exc:
        service.require_membership(tenant_id=tenant.id, user_id="owner-1")
    assert exc.value.code == "tenant_not_active"


def test_audit_events_are_append_only_records_in_store():
    service = _service()
    tenant = service.create_tenant(name="Brain", owner_user_id="owner-1")
    invite = service.create_invite(
        tenant_id=tenant.id,
        email="viewer@example.com",
        role=TenantRole.VIEWER,
        invited_by_user_id="owner-1",
        token="viewer-token",
    )
    service.accept_invite(token=invite.token, accepted_by_user_id="viewer-1")

    event_types = [event.event_type for event in service.store.audit_events]
    assert event_types == [
        "tenant.created",
        "membership.owner_created",
        "invite.created",
        "invite.accepted",
        "membership.joined",
    ]
    assert all(event.tenant_id == tenant.id for event in service.store.audit_events)
