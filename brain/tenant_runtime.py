from __future__ import annotations

import hashlib
import hmac
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterator, Mapping, TypeVar
from uuid import UUID

from .tenant_auth import TenantRole
from .tenant_context import TenantContext, TenantScopeViolation, trusted_tenant_context

T = TypeVar("T")

_active_tenant_context: ContextVar[TenantContext | None] = ContextVar(
    "brain_active_tenant_context", default=None
)


def active_tenant_context() -> TenantContext | None:
    return _active_tenant_context.get()


def set_active_tenant_context(context: TenantContext | None) -> Token:
    return _active_tenant_context.set(context)


def reset_active_tenant_context(token: Token) -> None:
    _active_tenant_context.reset(token)


@contextmanager
def tenant_context_scope(context: TenantContext | None) -> Iterator[None]:
    token = set_active_tenant_context(context)
    try:
        yield
    finally:
        reset_active_tenant_context(token)


class TenantScopedConnectionPool:
    """Pool facade that stamps verified tenant context into each transaction.

    The service-context bypass is deliberately absent. Only tenant and actor
    settings are exported; database-side trusted service access remains a role
    membership decision as defined by migration 019.
    """

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate

    @contextmanager
    def connection(self, *args: Any, **kwargs: Any) -> Iterator[Any]:
        with self.delegate.connection(*args, **kwargs) as conn:
            context = active_tenant_context()
            if context is not None:
                conn.execute(
                    "select set_config('brain.tenant_id', %s, true)",
                    (str(context.tenant_id),),
                )
                conn.execute(
                    "select set_config('brain.actor_id', %s, true)",
                    (context.actor_id,),
                )
            yield conn

    def close(self) -> None:
        self.delegate.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


@dataclass(frozen=True)
class TenantIdentity:
    tenant_id: UUID
    actor_id: str
    timestamp: int


@dataclass(frozen=True)
class TenantRequestSecurity:
    mode: str = "disabled"
    secret: str | None = None
    max_clock_skew_seconds: int = 300

    @classmethod
    def from_env(cls) -> "TenantRequestSecurity":
        mode = os.environ.get("BRAIN_TENANT_MODE", "disabled").strip().lower()
        if mode not in {"disabled", "optional", "required"}:
            raise RuntimeError("BRAIN_TENANT_MODE must be disabled, optional, or required")
        secret = os.environ.get("BRAIN_TENANT_CONTEXT_SECRET")
        if mode == "required" and not secret:
            raise RuntimeError("BRAIN_TENANT_CONTEXT_SECRET is required when tenant mode is required")
        return cls(mode=mode, secret=secret)

    def _message(self, identity: TenantIdentity) -> bytes:
        return f"{identity.tenant_id}\n{identity.actor_id}\n{identity.timestamp}".encode()

    def sign(self, identity: TenantIdentity) -> str:
        if not self.secret:
            raise TenantScopeViolation("tenant_context_secret_not_configured")
        return hmac.new(self.secret.encode(), self._message(identity), hashlib.sha256).hexdigest()

    def verify(self, identity: TenantIdentity, signature: str, *, now: int | None = None) -> None:
        if not self.secret:
            raise TenantScopeViolation("tenant_context_secret_not_configured")
        current = int(time.time()) if now is None else int(now)
        if abs(current - identity.timestamp) > self.max_clock_skew_seconds:
            raise TenantScopeViolation("tenant_context_signature_expired")
        expected = self.sign(identity)
        if not signature or not hmac.compare_digest(signature, expected):
            raise TenantScopeViolation("invalid_tenant_context_signature")

    def parse_and_verify(self, headers: Mapping[str, str], *, now: int | None = None) -> TenantContext | None:
        normalized = {key.lower(): value for key, value in headers.items()}
        if normalized.get("x-brain-roles"):
            raise TenantScopeViolation("tenant roles must come from verified membership")
        if normalized.get("x-brain-service-context"):
            raise TenantScopeViolation("service context cannot be asserted by request headers")

        raw_tenant = normalized.get("x-brain-tenant-id")
        actor_id = normalized.get("x-brain-actor-id")
        raw_timestamp = normalized.get("x-brain-tenant-timestamp")
        signature = normalized.get("x-brain-tenant-signature", "")
        supplied = any((raw_tenant, actor_id, raw_timestamp, signature))

        if not supplied:
            if self.mode == "required":
                raise TenantScopeViolation("tenant_context_required")
            return None
        if not raw_tenant or not actor_id or not raw_timestamp or not signature:
            raise TenantScopeViolation("signed_tenant_context_incomplete")
        if not actor_id.strip():
            raise TenantScopeViolation("tenant context requires actor identity")
        try:
            tenant_id = UUID(raw_tenant)
            timestamp = int(raw_timestamp)
        except (TypeError, ValueError) as exc:
            raise TenantScopeViolation("invalid_signed_tenant_context") from exc

        identity = TenantIdentity(tenant_id=tenant_id, actor_id=actor_id, timestamp=timestamp)
        self.verify(identity, signature, now=now)
        return trusted_tenant_context(tenant_id=tenant_id, actor_id=actor_id, roles=())


class PostgresTenantMembershipResolver:
    """Resolve roles from durable membership state under signed tenant context."""

    def __init__(self, pool: Any) -> None:
        self.pool = pool

    def resolve(self, identity_context: TenantContext) -> TenantContext:
        with tenant_context_scope(identity_context):
            with self.pool.connection() as conn:
                row = conn.execute(
                    """
                    select m.role
                    from public.tenant_memberships m
                    join public.tenants t on t.id = m.tenant_id
                    where m.tenant_id = %s
                      and m.user_id = %s
                      and m.status = 'active'
                      and t.status = 'active'
                    """,
                    (identity_context.tenant_id, identity_context.actor_id),
                ).fetchone()
        if not row:
            raise TenantScopeViolation("active_tenant_membership_required")
        role = TenantRole(str(row[0]))
        return trusted_tenant_context(
            tenant_id=identity_context.tenant_id,
            actor_id=identity_context.actor_id,
            roles=(role,),
        )


class TenantPartitionedFactory(Generic[T]):
    """Create one mutable service instance per tenant, plus a legacy system partition."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self.factory = factory
        self.instances: dict[str, T] = {}

    def _partition_key(self) -> str:
        context = active_tenant_context()
        return str(context.tenant_id) if context is not None else "__system__"

    def current(self) -> T:
        key = self._partition_key()
        if key not in self.instances:
            self.instances[key] = self.factory()
        return self.instances[key]

    def __getattr__(self, name: str) -> Any:
        return getattr(self.current(), name)


@dataclass
class TenantServiceBundle:
    store: Any
    runtime: Any
    learning: Any
    heartbeat: Any
    money_spine: Any


class TenantServiceRegistry(TenantPartitionedFactory[TenantServiceBundle]):
    pass


class BundleAttributeProxy:
    def __init__(self, registry: TenantServiceRegistry, attribute: str) -> None:
        self.registry = registry
        self.attribute = attribute

    def current(self) -> Any:
        return getattr(self.registry.current(), self.attribute)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.current(), name)
