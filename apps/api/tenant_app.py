from __future__ import annotations

import importlib
import os
from typing import Any

from fastapi.responses import JSONResponse

from brain.adapters.brain_store import PostgresBrainStore
from brain.adapters.cognition import PostgresCognitiveOrganismStore
from brain.adapters.learning_store import (
    PostgresAttributionStore,
    PostgresEdgeStore,
    PostgresPredictionStore,
    PostgresSourceStore,
)
from brain.cognitive_organism import CognitiveOrganism
from brain.heartbeat import HeartbeatService
from brain.learning import LearningService
from brain.money_spine import MoneySpineService
from brain.runtime import BrainRuntime
from brain.tenant_auth import TenantRole
from brain.tenant_context import TenantScopeViolation
from brain.tenant_runtime import (
    BundleAttributeProxy,
    PostgresTenantMembershipResolver,
    TenantPartitionedFactory,
    TenantRequestSecurity,
    TenantScopedConnectionPool,
    TenantServiceBundle,
    TenantServiceRegistry,
    active_tenant_context,
    require_safe_runtime_role,
    tenant_context_scope,
    tenant_rls_enforced,
)

try:
    from psycopg_pool import ConnectionPool
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    ConnectionPool = None
    Jsonb = None

# Prevent the legacy module import from opening an unscoped database store before
# signed tenant context exists. Importlib keeps all static imports above this
# initialization boundary so linting can enforce normal import ordering.
_DATABASE_URL = os.environ.pop("DATABASE_URL", None)
try:
    base = importlib.import_module("apps.api.main")
    organism_routes = importlib.import_module("apps.api.cognitive_organism_routes")
finally:
    if _DATABASE_URL is not None:
        os.environ["DATABASE_URL"] = _DATABASE_URL


class TenantAwareCognitiveOrganismStore(PostgresCognitiveOrganismStore):
    """Checkpoint adapter whose constant checkpoint names are tenant-local."""

    def save_checkpoint(self, checkpoint_name: str, payload: dict[str, Any]) -> None:
        from brain.adapters.cognition import _organism_payload

        encoded = dict(_organism_payload(payload))
        context = active_tenant_context()
        with self.pool.connection() as conn:
            if context is None:
                conn.execute(
                    """
                    insert into public.cognitive_organism_checkpoints (
                        checkpoint_name, payload, tenant_id, updated_at
                    ) values (%s, %s, null, now())
                    on conflict (checkpoint_name) where tenant_id is null do update set
                        payload = excluded.payload, updated_at = now()
                    """,
                    (checkpoint_name, Jsonb(encoded)),
                )
            else:
                conn.execute(
                    """
                    insert into public.cognitive_organism_checkpoints (
                        checkpoint_name, payload, tenant_id, updated_at
                    ) values (%s, %s, %s, now())
                    on conflict (tenant_id, checkpoint_name) where tenant_id is not null do update set
                        payload = excluded.payload, updated_at = now()
                    """,
                    (checkpoint_name, Jsonb(encoded), context.tenant_id),
                )
            conn.execute(
                """
                insert into public.organism_audit_events (
                    event_type, object_type, object_id, payload
                ) values (%s, %s, %s, %s)
                """,
                (
                    "COGNITIVE_ORGANISM_CHECKPOINT_SAVED",
                    "cognitive_organism_checkpoint",
                    checkpoint_name,
                    Jsonb(encoded),
                ),
            )
            conn.commit()

    def load_checkpoint(self, checkpoint_name: str) -> dict[str, Any] | None:
        context = active_tenant_context()
        with self.pool.connection() as conn:
            if context is None:
                row = conn.execute(
                    """
                    select payload from public.cognitive_organism_checkpoints
                    where tenant_id is null and checkpoint_name = %s
                    """,
                    (checkpoint_name,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    select payload from public.cognitive_organism_checkpoints
                    where tenant_id = %s and checkpoint_name = %s
                    """,
                    (context.tenant_id, checkpoint_name),
                ).fetchone()
        return dict(row[0]) if row else None


app = base.app
tenant_security = TenantRequestSecurity.from_env()

if tenant_security.mode == "required" and not _DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required when BRAIN_TENANT_MODE=required")

_raw_pool = None
_scoped_pool = None
_membership_resolver = None
_service_registry = None

if _DATABASE_URL:
    if ConnectionPool is None:
        raise RuntimeError("PostgreSQL support requires project dependencies")
    _raw_pool = ConnectionPool(conninfo=_DATABASE_URL, min_size=1, max_size=20, open=True)
    with _raw_pool.connection() as conn:
        if tenant_rls_enforced(conn):
            if tenant_security.mode != "required":
                raise RuntimeError(
                    "BRAIN_TENANT_MODE=required when tenant RLS is enforced"
                )
            require_safe_runtime_role(conn, require_trusted_service=False)

    _scoped_pool = TenantScopedConnectionPool(_raw_pool)
    _membership_resolver = PostgresTenantMembershipResolver(_scoped_pool)

    def _build_bundle() -> TenantServiceBundle:
        store = PostgresBrainStore(_DATABASE_URL, pool=_scoped_pool)
        learning = LearningService(
            store.event_store,
            predictions=PostgresPredictionStore(store.pool),
            edges=PostgresEdgeStore(store.pool),
            attributions=PostgresAttributionStore(store.pool),
            sources=PostgresSourceStore(store.pool),
        )
        runtime = BrainRuntime(store=store)
        heartbeat = HeartbeatService(event_store=store.event_store, learning=learning)
        return TenantServiceBundle(
            store=store,
            runtime=runtime,
            learning=learning,
            heartbeat=heartbeat,
            money_spine=MoneySpineService(),
        )

    _service_registry = TenantServiceRegistry(_build_bundle)
    base._brain_store = BundleAttributeProxy(_service_registry, "store")
    base.runtime = BundleAttributeProxy(_service_registry, "runtime")
    base.learning = BundleAttributeProxy(_service_registry, "learning")
    base.heartbeat = BundleAttributeProxy(_service_registry, "heartbeat")
    base.money_spine = BundleAttributeProxy(_service_registry, "money_spine")

    # Not evictable: CognitiveOrganism is constructed empty and is never
    # hydrated from organism_store, so dropping a tenant's instance would reset
    # its workspace, agency actions and curiosity tasks rather than reload them.
    organism_routes.organism = TenantPartitionedFactory(CognitiveOrganism, evictable=False)
    organism_routes.organism_store = TenantAwareCognitiveOrganismStore(pool=_scoped_pool)
    organism_routes.startup_checkpoint = None


@app.middleware("http")
async def tenant_membership_boundary(request, call_next):
    if request.url.path in {"/health", "/ready"} or tenant_security.mode == "disabled":
        return await call_next(request)

    try:
        identity_context = tenant_security.parse_and_verify(request.headers)
    except TenantScopeViolation as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    if identity_context is None:
        return await call_next(request)
    if _membership_resolver is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "tenant_membership_store_unavailable"},
        )

    try:
        verified = _membership_resolver.resolve(identity_context)
        if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            verified.require_role(TenantRole.OWNER, TenantRole.ADMIN, TenantRole.OPERATOR)
    except TenantScopeViolation as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "tenant_membership_lookup_failed"})

    with tenant_context_scope(verified):
        return await call_next(request)
