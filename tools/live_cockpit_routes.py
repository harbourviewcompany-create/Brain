from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi.responses import JSONResponse

import apps.api.tenant_app as tenant_api
from brain.logging_config import get_logger
from brain.tenant_auth import TenantRole
from brain.tenant_context import TenantScopeViolation, trusted_tenant_context
from brain.tenant_runtime import tenant_context_scope
from tools.vercel_oidc import VercelOidcVerifier

# Railway's cockpit compatibility surface is registered on the same tenant-aware
# FastAPI object used by the canonical production API. This preserves the live
# read-model routes while ensuring forced-RLS startup and request membership
# checks cannot be bypassed by the compatibility entrypoint.
brain_api = tenant_api.base
app = tenant_api.app
runtime = brain_api.runtime
_learning_store = brain_api._learning_store

_logger = get_logger("live_cockpit_routes")

# This identifier is inert unless the explicit Observatory compatibility release
# SQL has created the tenant + durable membership. Canonical migrations 019-022
# deliberately leave pre-tenant NULL ownership quarantined.
_DEFAULT_OBSERVATORY_TENANT_ID = UUID("7d4427c4-8b8d-4f4a-9f75-b46cedc2f126")
_OBSERVATORY_ACTOR_ID = "brain-observatory-bff"


def _observatory_identity_context():
    raw = (os.environ.get("BRAIN_OBSERVATORY_TENANT_ID") or "").strip()
    try:
        tenant_id = UUID(raw) if raw else _DEFAULT_OBSERVATORY_TENANT_ID
    except ValueError:
        return None
    return trusted_tenant_context(
        tenant_id=tenant_id,
        actor_id=_OBSERVATORY_ACTOR_ID,
        roles=(),
    )


def _iso(value: Any | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _stable_uuid(namespace: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"brain:{namespace}:{key}"))


# The cockpit read model (GET /signals, /edges, /contradictions, /curiosity,
# /sources, /approvals, /opportunities, /outcomes, /formula-runs and
# /acceptance-reports) now lives in apps/api/cockpit_read_routes.py and is
# registered by apps/api/main.py, so the canonical Dockerfile image serves it
# too. Importing apps.api.tenant_app above brings those routes in; this module
# adds only the Vercel OIDC bridge on top.


class VercelOidcAuthBridge:
    """Railway deployment-identity bridge with durable tenant membership.

    A verified Vercel deployment token is exchanged for the local API key and
    bound to a server-owned tenant/actor identity. The actor's role is resolved
    from tenant_memberships before the request runs. Neither API key, tenant, role,
    nor service context is accepted from untrusted request headers through this
    bridge. Canonical legacy ownership remains quarantined until the separate
    Observatory compatibility release action has been explicitly applied.
    """

    def __init__(self, inner_app) -> None:
        self.inner_app = inner_app
        self.verifier = VercelOidcVerifier.from_env()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.inner_app(scope, receive, send)
            return

        headers = list(scope.get("headers", []))
        authorization = next(
            (
                value.decode("latin-1")
                for name, value in headers
                if name.lower() == b"authorization"
            ),
            "",
        )

        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
            verified, reason = self.verifier.verify(token)
            if verified:
                local_key = (os.environ.get("BRAIN_API_KEY") or "").strip()
                if not local_key:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "brain_local_api_key_not_configured"},
                    )
                    await response(scope, receive, send)
                    return

                identity_context = _observatory_identity_context()
                if identity_context is None:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "brain_observatory_tenant_invalid"},
                    )
                    await response(scope, receive, send)
                    return
                if tenant_api._membership_resolver is None:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "tenant_membership_store_unavailable"},
                    )
                    await response(scope, receive, send)
                    return

                try:
                    context = tenant_api._membership_resolver.resolve(identity_context)
                    if str(scope.get("method", "GET")).upper() not in {
                        "GET",
                        "HEAD",
                        "OPTIONS",
                    }:
                        context.require_role(
                            TenantRole.OWNER,
                            TenantRole.ADMIN,
                            TenantRole.OPERATOR,
                        )
                except TenantScopeViolation:
                    response = JSONResponse(
                        status_code=403,
                        content={"detail": "brain_observatory_membership_or_role_required"},
                    )
                    await response(scope, receive, send)
                    return
                except Exception:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "tenant_membership_lookup_failed"},
                    )
                    await response(scope, receive, send)
                    return

                blocked = {
                    b"authorization",
                    b"x-api-key",
                    b"x-brain-api-key",
                    b"x-brain-tenant-id",
                    b"x-brain-actor-id",
                    b"x-brain-tenant-timestamp",
                    b"x-brain-tenant-signature",
                    b"x-brain-roles",
                    b"x-brain-service-context",
                }
                scope = dict(scope)
                scope["headers"] = [
                    (name, value) for name, value in headers if name.lower() not in blocked
                ] + [(b"x-brain-api-key", local_key.encode("utf-8"))]

                with tenant_context_scope(context):
                    await self.inner_app(scope, receive, send)
                return
            if reason != "vercel_oidc_not_configured":
                _logger.info("vercel_oidc_auth_rejected reason=%s", reason)

        await self.inner_app(scope, receive, send)


# Uvicorn imports this module-level name. Cockpit routes remain registered on the
# tenant-aware FastAPI object above; only the Railway entrypoint is wrapped.
app = VercelOidcAuthBridge(app)
