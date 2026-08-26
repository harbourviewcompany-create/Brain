from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Generic, Iterator, Mapping, TypeVar
from uuid import UUID

from .logging_config import get_logger
from .tenant_auth import TenantRole
from .tenant_context import TenantContext, TenantScopeViolation, trusted_tenant_context

log = get_logger("tenant_runtime")

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


@dataclass(frozen=True)
class DatabaseRoleState:
    role_name: str
    is_database_owner: bool
    is_superuser: bool
    bypass_rls: bool
    runtime_member: bool
    trusted_service_member: bool


def inspect_database_role(conn: Any) -> DatabaseRoleState:
    """Inspect the connected PostgreSQL login without changing role state."""
    row = conn.execute(
        """
        select
          current_user,
          r.rolsuper,
          r.rolbypassrls,
          d.datdba = r.oid as is_database_owner,
          case
            when to_regrole('brain_runtime_role') is null then false
            else pg_has_role(current_user, 'brain_runtime_role', 'member')
          end as runtime_member,
          case
            when to_regrole('brain_trusted_service_role') is null then false
            else pg_has_role(current_user, 'brain_trusted_service_role', 'member')
          end as trusted_service_member
        from pg_roles r
        join pg_database d on d.datname = current_database()
        where r.rolname = current_user
        """
    ).fetchone()
    if not row:
        raise RuntimeError("unable to inspect current PostgreSQL role")
    return DatabaseRoleState(
        role_name=str(row[0]),
        is_superuser=bool(row[1]),
        bypass_rls=bool(row[2]),
        is_database_owner=bool(row[3]),
        runtime_member=bool(row[4]),
        trusted_service_member=bool(row[5]),
    )


def tenant_rls_enforced(conn: Any) -> bool:
    """Return true only when the critical tenant tables all FORCE RLS."""
    row = conn.execute(
        """
        select count(*) = 4 and bool_and(c.relrowsecurity and c.relforcerowsecurity)
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public'
          and c.relname in ('brain_events', 'beliefs', 'sensory_inbox', 'predictions')
        """
    ).fetchone()
    return bool(row and row[0])


def require_safe_runtime_role(
    conn: Any,
    *,
    require_trusted_service: bool,
) -> DatabaseRoleState:
    """Fail closed if a tenant-RLS runtime uses an owner/BYPASSRLS login.

    API/cockpit runtimes must be ordinary ``brain_runtime_role`` members and
    must not inherit the trusted-service bypass. The continuous worker may use
    the separately audited trusted-service group until tenant-by-tenant worker
    scheduling is implemented.
    """
    state = inspect_database_role(conn)
    violations: list[str] = []
    if state.is_database_owner:
        violations.append("database_owner")
    if state.is_superuser:
        violations.append("superuser")
    if state.bypass_rls:
        violations.append("bypassrls")
    if not state.runtime_member:
        violations.append("missing_brain_runtime_role")
    if require_trusted_service and not state.trusted_service_member:
        violations.append("missing_brain_trusted_service_role")
    if not require_trusted_service and state.trusted_service_member:
        violations.append("unexpected_brain_trusted_service_role")
    if violations:
        raise RuntimeError(
            "unsafe tenant RLS database role "
            f"{state.role_name}: {', '.join(violations)}"
        )
    return state


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


#: Partition that serves requests arriving without verified tenant context.
SYSTEM_PARTITION = "__system__"

#: Resident per-tenant instances allowed before the least recently used one is
#: evicted. Each bundle holds a full in-memory projection of its tenant's belief
#: graph, so an unbounded map grows with the tenant count for the life of the
#: process.
DEFAULT_PARTITION_LIMIT = 64


def _partition_limit() -> int:
    raw = os.environ.get("BRAIN_TENANT_BUNDLE_LIMIT")
    if not raw:
        return DEFAULT_PARTITION_LIMIT
    try:
        limit = int(raw)
    except ValueError as exc:
        raise RuntimeError("BRAIN_TENANT_BUNDLE_LIMIT must be an integer") from exc
    if limit < 1:
        raise RuntimeError("BRAIN_TENANT_BUNDLE_LIMIT must be at least 1")
    return limit


class TenantPartitionedFactory(Generic[T]):
    """One mutable service instance per tenant, bounded and built under a lock.

    Two problems motivated the bookkeeping here. The map was unbounded, so a
    process accumulated one resident belief-graph projection per tenant it had
    ever served. And the check-then-set was unsynchronized: FastAPI runs sync
    route handlers in a threadpool, so two concurrent first-requests for one
    tenant could each build an instance and silently discard one -- losing every
    mutation written to the orphan.
    """

    def __init__(self, factory: Callable[[], T], *, limit: int | None = None) -> None:
        self.factory = factory
        self.limit = limit if limit is not None else _partition_limit()
        # Ordered by least-recently-used first.
        self.instances: "OrderedDict[str, T]" = OrderedDict()
        self._lock = RLock()

    def _partition_key(self) -> str:
        context = active_tenant_context()
        return str(context.tenant_id) if context is not None else SYSTEM_PARTITION

    def current(self) -> T:
        key = self._partition_key()
        with self._lock:
            existing = self.instances.get(key)
            if existing is not None:
                self.instances.move_to_end(key)
                return existing

            instance = self.factory()
            self.instances[key] = instance
            self._evict_if_needed()
            return instance

    def _evict_if_needed(self) -> None:
        """Drop least-recently-used tenants, never the system partition.

        Caller holds the lock. Evicting only drops the in-memory projection;
        PostgreSQL remains authoritative, so the next request for that tenant
        rebuilds from the database.
        """

        while len(self.instances) > self.limit:
            for key in list(self.instances):
                if key == SYSTEM_PARTITION:
                    continue
                evicted = self.instances.pop(key)
                closer = getattr(evicted, "close", None)
                if callable(closer):
                    try:
                        closer()
                    except Exception:
                        log.exception("evicted tenant instance failed to close", extra={"partition": key})
                log.info("evicted least recently used tenant partition", extra={"partition": key})
                break
            else:
                # Only the system partition remains; nothing further to evict.
                return

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
