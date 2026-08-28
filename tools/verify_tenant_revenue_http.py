"""Production-shaped tenant HTTP verification for PR #183 revenue persistence.

Runs the canonical ``apps.api.tenant_app`` entrypoint against a disposable
PostgreSQL database using a non-owner ``brain_runtime_role`` login. It proves
that signed tenant requests persist signal -> score -> offer -> approval-required
action state with tenant ownership, and that a second tenant cannot read the action.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from fastapi.testclient import TestClient

from brain.tenant_runtime import TenantIdentity, TenantRequestSecurity

TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ACTOR_A = "revenue-http-operator-a"
ACTOR_B = "revenue-http-operator-b"

_SIGNAL = {
    "raw_signal": "Tenant buyer posted an urgent verified supplier request",
    "source_id": "tenant-http-source",
    "money_lane_id": "high_intent_lead_pack",
    "evidence_refs": ["https://example.test/tenant-http-signal"],
    "named_buyer": "Tenant Buyer",
    "decision_maker": "Operations Lead",
    "visible_pain": "Needs a qualified supplier now",
    "urgency_reason": "Public urgent request",
    "payment_path": "Package the verified lead for an approved manual action",
    "contact_channel": "buyer@example.test",
    "commercial_value": 0.8,
    "confidence": 0.9,
    "urgency": 0.9,
    "contactability": 0.9,
    "execution_difficulty": 0.2,
    "legal_access_risk": 0.0,
    "time_delay": 0.1,
    "metadata": {"verification": "tenant-revenue-http"},
}


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _seed_tenants(admin_dsn: str) -> None:
    with psycopg.connect(admin_dsn) as conn:
        conn.execute(
            """
            insert into public.tenants (id, name, slug, status)
            values
              (%s, 'Revenue HTTP A', 'revenue-http-a', 'active'),
              (%s, 'Revenue HTTP B', 'revenue-http-b', 'active')
            on conflict (id) do update set status = 'active'
            """,
            (TENANT_A, TENANT_B),
        )
        conn.execute(
            """
            insert into public.tenant_memberships (tenant_id, user_id, role, status)
            values
              (%s, %s, 'operator', 'active'),
              (%s, %s, 'operator', 'active')
            on conflict (tenant_id, user_id) do update set
              role = excluded.role,
              status = excluded.status,
              removed_at = null
            """,
            (TENANT_A, ACTOR_A, TENANT_B, ACTOR_B),
        )
        conn.commit()


def _headers(tenant_id: UUID, actor_id: str) -> dict[str, str]:
    security = TenantRequestSecurity.from_env()
    identity = TenantIdentity(
        tenant_id=tenant_id,
        actor_id=actor_id,
        timestamp=int(time.time()),
    )
    return {
        "x-api-key": _required_env("BRAIN_API_KEY"),
        "x-brain-tenant-id": str(tenant_id),
        "x-brain-actor-id": actor_id,
        "x-brain-tenant-timestamp": str(identity.timestamp),
        "x-brain-tenant-signature": security.sign(identity),
    }


def _assert_owned(admin_dsn: str, table: str, row_id: str, tenant_id: UUID) -> None:
    allowed = {
        "revenue_signals",
        "scored_revenue_opportunities",
        "packaged_offers",
        "revenue_execution_actions",
    }
    if table not in allowed:
        raise AssertionError(f"unexpected table: {table}")
    with psycopg.connect(admin_dsn) as conn:
        row = conn.execute(
            f"select tenant_id from public.{table} where id = %s",
            (UUID(row_id),),
        ).fetchone()
    assert row is not None, f"missing {table} row {row_id}"
    assert row[0] == tenant_id, f"{table} row has wrong tenant: {row[0]}"


def main() -> int:
    admin_dsn = _required_env("VERIFY_DATABASE_URL")
    _required_env("DATABASE_URL")
    _required_env("BRAIN_TENANT_CONTEXT_SECRET")
    _required_env("BRAIN_API_KEY")
    if os.environ.get("BRAIN_TENANT_MODE") != "required":
        raise RuntimeError("BRAIN_TENANT_MODE=required is required")

    _seed_tenants(admin_dsn)

    # Import only after environment and durable tenant fixtures are ready. This is
    # the canonical Docker/Railway/Fly tenant-aware entrypoint under test.
    from apps.api import tenant_app

    client = TestClient(tenant_app.app)
    headers_a = _headers(TENANT_A, ACTOR_A)
    headers_b = _headers(TENANT_B, ACTOR_B)

    packaged = client.post("/revenue-signals/package", json=_SIGNAL, headers=headers_a)
    assert packaged.status_code == 200, packaged.text
    packaged_body = packaged.json()
    assert packaged_body["score"]["actionable"] is True
    assert packaged_body["offer"]["offer_name"] == "High-Intent Lead Pack"

    queued = client.post(
        "/revenue-actions/queue",
        json={"signal": {**_SIGNAL, "raw_signal": "Tenant buyer needs a second approved lead package"}},
        headers=headers_a,
    )
    assert queued.status_code == 200, queued.text
    queued_body = queued.json()
    assert queued_body["action"]["state"] == "approval_required"
    action_id = queued_body["action"]["id"]

    _assert_owned(admin_dsn, "revenue_signals", packaged_body["score"]["signal_id"], TENANT_A)
    _assert_owned(admin_dsn, "scored_revenue_opportunities", packaged_body["score"]["id"], TENANT_A)
    _assert_owned(admin_dsn, "packaged_offers", packaged_body["offer"]["id"], TENANT_A)
    _assert_owned(admin_dsn, "revenue_signals", queued_body["score"]["signal_id"], TENANT_A)
    _assert_owned(admin_dsn, "scored_revenue_opportunities", queued_body["score"]["id"], TENANT_A)
    _assert_owned(admin_dsn, "packaged_offers", queued_body["offer"]["id"], TENANT_A)
    _assert_owned(admin_dsn, "revenue_execution_actions", action_id, TENANT_A)

    with psycopg.connect(admin_dsn) as conn:
        action_row = conn.execute(
            "select state, approval_required from public.revenue_execution_actions where id = %s",
            (UUID(action_id),),
        ).fetchone()
    assert action_row == ("approval_required", True)

    hidden = client.get(f"/revenue-actions/{action_id}", headers=headers_b)
    assert hidden.status_code == 404, hidden.text
    second_snapshot = client.get("/revenue-actions", headers=headers_b)
    assert second_snapshot.status_code == 200, second_snapshot.text
    assert second_snapshot.json()["queued"] == 0

    print(
        "TENANT_REVENUE_HTTP_GO: canonical tenant_app persisted tenant-owned "
        "signal/score/offer/approval rows and isolated the action from a second tenant"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
