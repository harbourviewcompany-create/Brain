from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from brain.tenant_auth import TenantRole


class TenantScopeViolation(PermissionError):
    """Raised when an operation is attempted outside the active tenant scope."""


@dataclass(frozen=True)
class TenantContext:
    """Application-layer tenant context for scoped Brain operations.

    PR 3 introduces this as a narrow helper. Existing cognitive routes are not
    fully retrofitted here; later PRs must thread this context through each
    repository/service/API path before those paths can be considered tenant-safe.

    Roles and service-context status must come from verified membership or a
    trusted internal construction path. They must not be trusted from external
    request headers.
    """

    tenant_id: UUID
    actor_id: str
    roles: tuple[TenantRole, ...]
    service_context: bool = False

    def has_role(self, *allowed: TenantRole) -> bool:
        if self.service_context:
            return True
        return any(role in allowed for role in self.roles)

    def require_role(self, *allowed: TenantRole) -> None:
        if not self.has_role(*allowed):
            allowed_names = ",".join(role.value for role in allowed)
            raise TenantScopeViolation(f"actor lacks required tenant role: {allowed_names}")

    def require_same_tenant(self, tenant_id: UUID) -> None:
        if tenant_id != self.tenant_id:
            raise TenantScopeViolation("cross_tenant_access_denied")

    @property
    def sql_settings(self) -> dict[str, str]:
        """Return only tenant/actor settings safe for normal runtime sessions.

        Trusted service bypass is intentionally not exported as a user-defined
        session setting. Database-side service access is derived from a trusted
        PostgreSQL role in the PR 3 migration, not from request headers or GUCs.
        """

        return {
            "brain.tenant_id": str(self.tenant_id),
            "brain.actor_id": self.actor_id,
        }


def _headers_lower(headers: Mapping[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def trusted_tenant_context(
    *,
    tenant_id: UUID,
    actor_id: str,
    roles: tuple[TenantRole, ...],
    service_context: bool = False,
) -> TenantContext:
    """Construct a context from verified membership or internal service code only."""

    if not actor_id:
        raise TenantScopeViolation("tenant context requires actor identity")
    return TenantContext(
        tenant_id=tenant_id,
        actor_id=actor_id,
        roles=roles,
        service_context=service_context,
    )


def parse_tenant_context_headers(headers: Mapping[str, str]) -> TenantContext | None:
    """Parse transitional tenant identity headers without trusting privileges.

    Header names are intentionally explicit and Brain-specific. Returning None
    lets existing PR 2 API-key behavior continue unchanged while later PRs move
    individual routes from optional parsing to required verified tenant context.

    External headers may identify the tenant and actor during the transition,
    but they may not assert roles or service-context status. Later routes must
    resolve roles from tenant membership records before calling `require_role`.
    """

    normalized = _headers_lower(headers)
    tenant_id = normalized.get("x-brain-tenant-id")
    actor_id = normalized.get("x-brain-actor-id")
    raw_roles = normalized.get("x-brain-roles")
    raw_service_context = normalized.get("x-brain-service-context")

    if raw_roles:
        raise TenantScopeViolation("tenant roles must come from verified membership")
    if raw_service_context:
        raise TenantScopeViolation("service context cannot be asserted by request headers")

    if not tenant_id and not actor_id:
        return None
    if not tenant_id or not actor_id:
        raise TenantScopeViolation("tenant context requires tenant and actor headers")
    if not actor_id.strip():
        raise TenantScopeViolation("tenant context requires actor identity")

    try:
        parsed_tenant_id = UUID(tenant_id)
    except (TypeError, ValueError) as exc:
        raise TenantScopeViolation("invalid_tenant_id") from exc

    return TenantContext(
        tenant_id=parsed_tenant_id,
        actor_id=actor_id,
        roles=(),
        service_context=False,
    )
