from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4


class TenantAuthError(Exception):
    """Domain error with a stable machine-readable code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class TenantRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


_ROLE_RANK = {
    TenantRole.VIEWER: 10,
    TenantRole.OPERATOR: 20,
    TenantRole.ADMIN: 30,
    TenantRole.OWNER: 40,
}


@dataclass(frozen=True)
class Tenant:
    id: UUID
    name: str
    slug: str
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    archived_at: datetime | None = None


@dataclass(frozen=True)
class TenantMembership:
    id: UUID
    tenant_id: UUID
    user_id: str
    role: TenantRole
    status: MembershipStatus = MembershipStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    removed_at: datetime | None = None


@dataclass(frozen=True)
class TenantInvite:
    id: UUID
    tenant_id: UUID
    email: str
    role: TenantRole
    token: str
    invited_by_user_id: str
    status: InviteStatus = InviteStatus.PENDING
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC) + timedelta(days=7))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    accepted_by_user_id: str | None = None
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class TenantAuditEvent:
    id: UUID
    tenant_id: UUID
    actor_user_id: str
    event_type: str
    entity_type: str
    entity_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str | None = None


class InMemoryTenantAuthStore:
    """Testable in-memory store for tenant/auth lifecycle rules.

    This is the PR 2 domain foundation. It deliberately does not attempt to
    retrofit existing cognitive tables; PR 3 owns tenant_id migration/RLS for
    existing Brain state.
    """

    def __init__(self) -> None:
        self.tenants: dict[UUID, Tenant] = {}
        self.memberships: dict[UUID, TenantMembership] = {}
        self.invites: dict[str, TenantInvite] = {}
        self.audit_events: list[TenantAuditEvent] = []


class TenantAuthService:
    def __init__(self, store: InMemoryTenantAuthStore | None = None) -> None:
        self.store = store or InMemoryTenantAuthStore()

    def create_tenant(self, *, name: str, owner_user_id: str, slug: str | None = None) -> Tenant:
        if not name.strip():
            raise TenantAuthError("tenant_name_required")
        if not owner_user_id.strip():
            raise TenantAuthError("owner_user_id_required")
        tenant = Tenant(id=uuid4(), name=name.strip(), slug=slug or self._slugify(name))
        self.store.tenants[tenant.id] = tenant
        membership = TenantMembership(
            id=uuid4(),
            tenant_id=tenant.id,
            user_id=owner_user_id,
            role=TenantRole.OWNER,
        )
        self.store.memberships[membership.id] = membership
        self._audit(
            tenant_id=tenant.id,
            actor_user_id=owner_user_id,
            event_type="tenant.created",
            entity_type="tenant",
            entity_id=str(tenant.id),
        )
        self._audit(
            tenant_id=tenant.id,
            actor_user_id=owner_user_id,
            event_type="membership.owner_created",
            entity_type="tenant_membership",
            entity_id=str(membership.id),
        )
        return tenant

    def get_tenant(self, tenant_id: UUID) -> Tenant:
        tenant = self.store.tenants.get(tenant_id)
        if tenant is None:
            raise TenantAuthError("tenant_not_found")
        return tenant

    def get_membership(self, *, tenant_id: UUID, user_id: str) -> TenantMembership:
        for membership in self.store.memberships.values():
            if membership.tenant_id == tenant_id and membership.user_id == user_id:
                return membership
        raise TenantAuthError("membership_not_found")

    def list_memberships(self, tenant_id: UUID) -> list[TenantMembership]:
        return [m for m in self.store.memberships.values() if m.tenant_id == tenant_id]

    def require_membership(
        self,
        *,
        tenant_id: UUID,
        user_id: str,
        allowed_roles: set[TenantRole] | None = None,
    ) -> TenantMembership:
        tenant = self.get_tenant(tenant_id)
        if tenant.status != TenantStatus.ACTIVE:
            raise TenantAuthError("tenant_not_active")
        membership = self.get_membership(tenant_id=tenant_id, user_id=user_id)
        if membership.status != MembershipStatus.ACTIVE:
            raise TenantAuthError("membership_not_active")
        if allowed_roles is not None and membership.role not in allowed_roles:
            raise TenantAuthError("role_forbidden")
        return membership

    def create_invite(
        self,
        *,
        tenant_id: UUID,
        email: str,
        role: TenantRole,
        invited_by_user_id: str,
        token: str | None = None,
        expires_at: datetime | None = None,
    ) -> TenantInvite:
        self.require_membership(
            tenant_id=tenant_id,
            user_id=invited_by_user_id,
            allowed_roles={TenantRole.OWNER, TenantRole.ADMIN},
        )
        if role == TenantRole.OWNER:
            inviter = self.get_membership(tenant_id=tenant_id, user_id=invited_by_user_id)
            if inviter.role != TenantRole.OWNER:
                raise TenantAuthError("owner_invite_requires_owner")
        if not email.strip():
            raise TenantAuthError("invite_email_required")
        invite = TenantInvite(
            id=uuid4(),
            tenant_id=tenant_id,
            email=email.strip().lower(),
            role=role,
            token=token or uuid4().hex,
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at or (datetime.now(UTC) + timedelta(days=7)),
        )
        if invite.token in self.store.invites:
            raise TenantAuthError("invite_token_already_exists")
        self.store.invites[invite.token] = invite
        self._audit(
            tenant_id=tenant_id,
            actor_user_id=invited_by_user_id,
            event_type="invite.created",
            entity_type="tenant_invite",
            entity_id=str(invite.id),
        )
        return invite

    def accept_invite(
        self,
        *,
        token: str,
        accepted_by_user_id: str,
        now: datetime | None = None,
    ) -> TenantMembership:
        current_time = now or datetime.now(UTC)
        invite = self.store.invites.get(token)
        if invite is None:
            raise TenantAuthError("invite_not_found")
        if invite.status != InviteStatus.PENDING:
            raise TenantAuthError("invite_not_pending")
        if invite.expires_at <= current_time:
            expired = self._replace_invite(invite, status=InviteStatus.EXPIRED)
            self.store.invites[token] = expired
            raise TenantAuthError("invite_expired")
        tenant = self.get_tenant(invite.tenant_id)
        if tenant.status != TenantStatus.ACTIVE:
            raise TenantAuthError("tenant_not_active")

        existing = self._find_membership(tenant_id=invite.tenant_id, user_id=accepted_by_user_id)
        if existing and existing.status == MembershipStatus.ACTIVE:
            membership = existing
        else:
            membership = TenantMembership(
                id=uuid4(),
                tenant_id=invite.tenant_id,
                user_id=accepted_by_user_id,
                role=invite.role,
            )
            self.store.memberships[membership.id] = membership

        self.store.invites[token] = self._replace_invite(
            invite,
            status=InviteStatus.ACCEPTED,
            accepted_by_user_id=accepted_by_user_id,
            accepted_at=current_time,
        )
        self._audit(
            tenant_id=invite.tenant_id,
            actor_user_id=accepted_by_user_id,
            event_type="invite.accepted",
            entity_type="tenant_invite",
            entity_id=str(invite.id),
        )
        self._audit(
            tenant_id=invite.tenant_id,
            actor_user_id=accepted_by_user_id,
            event_type="membership.joined",
            entity_type="tenant_membership",
            entity_id=str(membership.id),
        )
        return membership

    def revoke_invite(self, *, tenant_id: UUID, token: str, actor_user_id: str) -> TenantInvite:
        self.require_membership(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            allowed_roles={TenantRole.OWNER, TenantRole.ADMIN},
        )
        invite = self.store.invites.get(token)
        if invite is None or invite.tenant_id != tenant_id:
            raise TenantAuthError("invite_not_found")
        if invite.status != InviteStatus.PENDING:
            raise TenantAuthError("invite_not_pending")
        revoked = self._replace_invite(invite, status=InviteStatus.REVOKED, revoked_at=datetime.now(UTC))
        self.store.invites[token] = revoked
        self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type="invite.revoked",
            entity_type="tenant_invite",
            entity_id=str(invite.id),
        )
        return revoked

    def change_member_role(
        self,
        *,
        tenant_id: UUID,
        target_user_id: str,
        new_role: TenantRole,
        actor_user_id: str,
    ) -> TenantMembership:
        actor = self.require_membership(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            allowed_roles={TenantRole.OWNER, TenantRole.ADMIN},
        )
        target = self.get_membership(tenant_id=tenant_id, user_id=target_user_id)
        if target.status != MembershipStatus.ACTIVE:
            raise TenantAuthError("membership_not_active")
        if actor.role != TenantRole.OWNER and _ROLE_RANK[new_role] >= _ROLE_RANK[TenantRole.ADMIN]:
            raise TenantAuthError("role_change_forbidden")
        if target.role == TenantRole.OWNER and new_role != TenantRole.OWNER:
            self._assert_not_last_owner(tenant_id)
        updated = TenantMembership(
            id=target.id,
            tenant_id=target.tenant_id,
            user_id=target.user_id,
            role=new_role,
            status=target.status,
            created_at=target.created_at,
            removed_at=target.removed_at,
        )
        self.store.memberships[target.id] = updated
        self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type="membership.role_changed",
            entity_type="tenant_membership",
            entity_id=str(target.id),
        )
        return updated

    def remove_member(
        self,
        *,
        tenant_id: UUID,
        target_user_id: str,
        actor_user_id: str,
    ) -> TenantMembership:
        self.require_membership(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            allowed_roles={TenantRole.OWNER, TenantRole.ADMIN},
        )
        target = self.get_membership(tenant_id=tenant_id, user_id=target_user_id)
        if target.status != MembershipStatus.ACTIVE:
            raise TenantAuthError("membership_not_active")
        if target.role == TenantRole.OWNER:
            self._assert_not_last_owner(tenant_id)
        removed = TenantMembership(
            id=target.id,
            tenant_id=target.tenant_id,
            user_id=target.user_id,
            role=target.role,
            status=MembershipStatus.REMOVED,
            created_at=target.created_at,
            removed_at=datetime.now(UTC),
        )
        self.store.memberships[target.id] = removed
        self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type="membership.removed",
            entity_type="tenant_membership",
            entity_id=str(target.id),
        )
        return removed

    def set_tenant_status(
        self,
        *,
        tenant_id: UUID,
        status: TenantStatus,
        actor_user_id: str,
        reason: str | None = None,
    ) -> Tenant:
        self.require_membership(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            allowed_roles={TenantRole.OWNER, TenantRole.ADMIN},
        )
        tenant = self.get_tenant(tenant_id)
        archived_at = datetime.now(UTC) if status == TenantStatus.ARCHIVED else None
        updated = Tenant(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=status,
            created_at=tenant.created_at,
            archived_at=archived_at,
        )
        self.store.tenants[tenant_id] = updated
        self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type=f"tenant.{status.value}",
            entity_type="tenant",
            entity_id=str(tenant_id),
            reason=reason,
        )
        return updated

    def _find_membership(self, *, tenant_id: UUID, user_id: str) -> TenantMembership | None:
        for membership in self.store.memberships.values():
            if membership.tenant_id == tenant_id and membership.user_id == user_id:
                return membership
        return None

    def _assert_not_last_owner(self, tenant_id: UUID) -> None:
        owners = [
            m
            for m in self.store.memberships.values()
            if m.tenant_id == tenant_id and m.role == TenantRole.OWNER and m.status == MembershipStatus.ACTIVE
        ]
        if len(owners) <= 1:
            raise TenantAuthError("cannot_remove_last_owner")

    def _audit(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        reason: str | None = None,
    ) -> None:
        self.store.audit_events.append(
            TenantAuditEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                reason=reason,
            )
        )

    @staticmethod
    def _replace_invite(invite: TenantInvite, **changes: object) -> TenantInvite:
        values = {
            "id": invite.id,
            "tenant_id": invite.tenant_id,
            "email": invite.email,
            "role": invite.role,
            "token": invite.token,
            "invited_by_user_id": invite.invited_by_user_id,
            "status": invite.status,
            "expires_at": invite.expires_at,
            "created_at": invite.created_at,
            "accepted_by_user_id": invite.accepted_by_user_id,
            "accepted_at": invite.accepted_at,
            "revoked_at": invite.revoked_at,
        }
        values.update(changes)
        return TenantInvite(**values)  # type: ignore[arg-type]

    @staticmethod
    def _slugify(value: str) -> str:
        slug = "-".join(value.lower().strip().split())
        return slug or uuid4().hex
