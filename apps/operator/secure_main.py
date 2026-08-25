from __future__ import annotations

import hmac
import importlib
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from brain.adapters.economic_store import PostgresEconomicStore
from brain.cognitive_organism import CognitiveOrganism
from brain.economic_runtime import EconomicRuntime, InMemoryEconomicStore
from brain.security import SecurityConfig
from brain.tenant_auth import TenantRole
from brain.tenant_context import TenantScopeViolation
from brain.tenant_runtime import (
    PostgresTenantMembershipResolver,
    TenantPartitionedFactory,
    TenantRequestSecurity,
    TenantScopedConnectionPool,
    tenant_context_scope,
)

try:
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover
    ConnectionPool = None

# Import the legacy operator surface without allowing its module-level bootstrap
# to open an unscoped PostgreSQL connection. The secure wrapper rebinds its
# mutable runtime services below and preserves every existing route/UI.
_DATABASE_URL_AT_IMPORT = os.environ.pop("DATABASE_URL", None)
try:
    legacy = importlib.import_module("apps.operator.main")
finally:
    if _DATABASE_URL_AT_IMPORT is not None:
        os.environ["DATABASE_URL"] = _DATABASE_URL_AT_IMPORT

_PUBLIC_PATHS = frozenset({"/health", "/ready"})
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _api_key_candidate(request: Request) -> str:
    authorization = request.headers.get("authorization")
    candidate = (
        request.headers.get("x-brain-api-key")
        or request.headers.get("x-api-key")
        or ""
    )
    if authorization and authorization.lower().startswith("bearer "):
        candidate = authorization[7:].strip()
    return candidate


def create_app() -> FastAPI:
    security = SecurityConfig.from_env()
    tenant_security = TenantRequestSecurity.from_env()
    database_url = os.environ.get("DATABASE_URL")

    if security.production and not database_url:
        raise RuntimeError("DATABASE_URL is required for the production operator plane")
    if security.production and tenant_security.mode != "required":
        raise RuntimeError("BRAIN_TENANT_MODE=required is required for the production operator plane")
    if tenant_security.mode == "required" and not database_url:
        raise RuntimeError("DATABASE_URL is required when operator tenant mode is required")

    app = FastAPI(title="Brain Secure Operator", version="0.3.0")
    origins = security.allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Api-Key",
            "X-Brain-Api-Key",
            "X-Brain-Tenant-Id",
            "X-Brain-Actor-Id",
            "X-Brain-Tenant-Timestamp",
            "X-Brain-Tenant-Signature",
        ],
    )

    raw_pool: Any | None = None
    scoped_pool: TenantScopedConnectionPool | None = None
    membership_resolver: PostgresTenantMembershipResolver | None = None

    if database_url:
        if ConnectionPool is None:
            raise RuntimeError("PostgreSQL support requires project dependencies")
        raw_pool = ConnectionPool(conninfo=database_url, min_size=1, max_size=10, open=True)
        scoped_pool = TenantScopedConnectionPool(raw_pool)
        membership_resolver = PostgresTenantMembershipResolver(scoped_pool)
        legacy.economic = TenantPartitionedFactory(
            lambda: EconomicRuntime(PostgresEconomicStore(pool=scoped_pool))
        )
    else:
        legacy.economic = TenantPartitionedFactory(
            lambda: EconomicRuntime(InMemoryEconomicStore())
        )

    # The current Cognitive Organism cockpit is a process-local read model. It
    # is partitioned per verified tenant so no mutable operator projection is
    # shared across tenants. Full durable object-graph rehydration remains a
    # separately tracked HOLD rather than being falsely claimed here.
    legacy.organism = TenantPartitionedFactory(CognitiveOrganism)

    @app.middleware("http")
    async def operator_security_boundary(request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        configured_key = os.environ.get("BRAIN_API_KEY")
        if not configured_key:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "BRAIN_API_KEY is not configured on this deployment; "
                        "refusing operator requests until it is set"
                    )
                },
            )
        candidate = _api_key_candidate(request)
        if not candidate or not hmac.compare_digest(candidate, configured_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "invalid_or_missing_api_key"},
            )

        try:
            identity_context = tenant_security.parse_and_verify(request.headers)
        except TenantScopeViolation as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})

        if identity_context is None:
            return await call_next(request)
        if membership_resolver is None:
            return JSONResponse(
                status_code=503,
                content={"detail": "tenant_membership_store_unavailable"},
            )

        try:
            verified = membership_resolver.resolve(identity_context)
            if request.method.upper() not in _SAFE_METHODS:
                verified.require_role(
                    TenantRole.OWNER,
                    TenantRole.ADMIN,
                    TenantRole.OPERATOR,
                )
        except TenantScopeViolation as exc:
            return JSONResponse(status_code=403, content={"detail": str(exc)})
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"detail": "tenant_membership_lookup_failed"},
            )

        with tenant_context_scope(verified):
            return await call_next(request)

    @app.get("/ready")
    def readiness():
        if raw_pool is None:
            return {
                "status": "ok",
                "durable": False,
                "surface": "secure-operator",
                "environment": security.environment,
                "tenant_mode": tenant_security.mode,
            }
        try:
            with raw_pool.connection() as conn:
                row = conn.execute("select 1").fetchone()
                if not row or row[0] != 1:
                    raise RuntimeError("database_readiness_probe_failed")
        except Exception:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "durable": True,
                    "surface": "secure-operator",
                    "reason": "database_unavailable",
                },
            )
        return {
            "status": "ok",
            "durable": True,
            "surface": "secure-operator",
            "environment": security.environment,
            "tenant_mode": tenant_security.mode,
        }

    app.mount("/", legacy.app)
    return app


app = create_app()
