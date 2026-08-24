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
        return {
            "brain.tenant_id": str(self.tenant_id),
            "brain.actor_id": self.actor_id,
            "brain.service_context": "true" if self.service_context else "false",
        }


def parse_tenant_context_headers(headers: Mapping[str, str]) -> TenantContext | None:
    """Parse tenant headers without enforcing that every route has them yet.

    Header names are intentionally explicit and Brain-specific. Returning None
    lets existing PR 2 API-key behavior continue unchanged while later PRs move
    individual routes from optional parsing to required tenant context.
    """

    tenant_id = headers.get("x-brain-tenant-id") or headers.get("X-Brain-Tenant-Id")
    actor_id = headers.get("x-brain-actor-id") or headers.get("X-Brain-Actor-Id")
    raw_roles = headers.get("x-brain-roles") or headers.get("X-Brain-Roles") or ""
    service_context = (
        headers.get("x-brain-service-context") or headers.get("X-Brain-Service-Context") or ""
    ).lower() == "true"

    if not tenant_id and not actor_id and not raw_roles and not service_context:
        return None
    if not tenant_id or not actor_id:
        raise TenantScopeViolation("tenant context requires tenant and actor headers")

    roles = tuple(TenantRole(role.strip()) for role in raw_roles.split(",") if role.strip())
    return TenantContext(
        tenant_id=UUID(tenant_id),
        actor_id=actor_id,
        roles=roles,
        service_context=service_context,
    )
