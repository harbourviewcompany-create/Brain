"""Production-shaped live-upgrade verification for PR #183.

Keeps the canonical tenant-aware API process alive while a disposable database
moves from migration 024 to 025. The probe proves three review contracts:

* a non-owner tenant runtime stays healthy before 025 even though the execution
  ledger is not yet granted to ``brain_runtime_role``;
* a store that observed the pre-025 signal schema begins audit persistence after
  025 without restarting the Python process; and
* tenant money/source learning survives service-bundle LRU eviction because the
  rebuilt bundle deterministically replays tenant-owned outcome rows.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from uuid import UUID

import psycopg
from fastapi.testclient import TestClient

from brain.tenant_runtime import TenantIdentity, TenantRequestSecurity

TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ACTOR_A = "revenue-upgrade-operator-a"
ACTOR_B = "revenue-upgrade-operator-b"


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
              (%s, 'Revenue Upgrade A', 'revenue-upgrade-a', 'active'),
              (%s, 'Revenue Upgrade B', 'revenue-upgrade-b', 'active')
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


def _signal(raw_signal: str) -> dict[str, object]:
    return {
        "raw_signal": raw_signal,
        "source_id": "tenant-upgrade-source",
        "money_lane_id": "high_intent_lead_pack",
        "evidence_refs": ["https://example.test/tenant-upgrade-signal"],
        "named_buyer": "Upgrade Buyer",
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
        "metadata": {"verification": "tenant-revenue-live-upgrade"},
    }


def _row_exists(admin_dsn: str, table: str, row_id: str) -> bool:
    allowed = {"revenue_signals", "scored_revenue_opportunities", "packaged_offers"}
    if table not in allowed:
        raise AssertionError(f"unexpected table: {table}")
    with psycopg.connect(admin_dsn) as conn:
        row = conn.execute(
            f"select 1 from public.{table} where id = %s",
            (UUID(row_id),),
        ).fetchone()
    return row is not None


def _apply_025(migrator_dsn: str) -> None:
    migration = Path("db/migrations/025_revenue_signal_source_lane_text_keys.sql")
    subprocess.run(
        ["psql", migrator_dsn, "-v", "ON_ERROR_STOP=1", "-f", str(migration)],
        check=True,
    )


def main() -> int:
    admin_dsn = _required_env("VERIFY_DATABASE_URL")
    _required_env("DATABASE_URL")
    migrator_dsn = _required_env("VERIFY_MIGRATION_DATABASE_URL")
    _required_env("BRAIN_TENANT_CONTEXT_SECRET")
    _required_env("BRAIN_API_KEY")
    if os.environ.get("BRAIN_TENANT_MODE") != "required":
        raise RuntimeError("BRAIN_TENANT_MODE=required is required")
    if os.environ.get("BRAIN_TENANT_BUNDLE_LIMIT") != "2":
        raise RuntimeError("BRAIN_TENANT_BUNDLE_LIMIT=2 is required for eviction proof")

    _seed_tenants(admin_dsn)

    # Import exactly once. Everything below, including migration 025, happens while
    # this module and its tenant service registry remain alive in the same process.
    from apps.api import tenant_app

    client = TestClient(tenant_app.app)
    headers_a = _headers(TENANT_A, ACTOR_A)
    headers_b = _headers(TENANT_B, ACTOR_B)

    health = client.get("/health")
    assert health.status_code == 200, health.text
    pre_snapshot = client.get("/revenue-actions", headers=headers_a)
    assert pre_snapshot.status_code == 200, pre_snapshot.text
    assert pre_snapshot.json()["actions"] == 0

    pre_package = client.post(
        "/revenue-signals/package",
        json=_signal("Pre-025 signal must remain operational without audit persistence"),
        headers=headers_a,
    )
    assert pre_package.status_code == 200, pre_package.text
    pre_body = pre_package.json()
    assert pre_body["score"]["actionable"] is True
    assert not _row_exists(admin_dsn, "revenue_signals", pre_body["score"]["signal_id"])
    print(
        "TENANT_REVENUE_PRE025_GO: non-owner canonical tenant runtime stayed healthy "
        "and safely skipped unavailable pre-025 revenue persistence"
    )

    # The same TenantRevenueStore instance has now observed a negative signal-audit
    # capability result. Apply 025 without restarting this Python process.
    _apply_025(migrator_dsn)

    post_package = client.post(
        "/revenue-signals/package",
        json=_signal("Post-025 signal must persist without process restart"),
        headers=headers_a,
    )
    assert post_package.status_code == 200, post_package.text
    post_body = post_package.json()
    assert _row_exists(admin_dsn, "revenue_signals", post_body["score"]["signal_id"])
    assert _row_exists(admin_dsn, "scored_revenue_opportunities", post_body["score"]["id"])
    assert _row_exists(admin_dsn, "packaged_offers", post_body["offer"]["id"])
    print(
        "SIGNAL_AUDIT_LIVE_UPGRADE_GO: cached pre-025 negative capability was "
        "rechecked and persistence activated without restart"
    )

    queued = client.post(
        "/revenue-actions/queue",
        json={"signal": _signal("Outcome learning must survive bundle eviction")},
        headers=headers_a,
    )
    assert queued.status_code == 200, queued.text
    action_id = queued.json()["action"]["id"]

    approved = client.post(
        f"/revenue-actions/{action_id}/approve",
        json={"approved_by": ACTOR_A},
        headers=headers_a,
    )
    assert approved.status_code == 200, approved.text

    outcome = client.post(
        f"/revenue-actions/{action_id}/outcome",
        json={
            "outcome_type": "paid_conversion",
            "revenue": 250.0,
            "reply": True,
            "meeting_booked": True,
            "paid_conversion": True,
            "legal_risk": 0.0,
            "operator_hours": 1.0,
            "lesson": "tenant learning survives eviction",
        },
        headers=headers_a,
    )
    assert outcome.status_code == 200, outcome.text

    before = client.get("/revenue-actions", headers=headers_a)
    assert before.status_code == 200, before.text
    before_body = before.json()
    before_source = before_body["source_scores"]["tenant-upgrade-source"]
    before_lane = before_body["lane_priorities"]["high_intent_lead_pack"]
    assert before_source != 0.5
    assert before_lane != 0.9

    # With the system partition plus tenant A resident and a limit of two, serving
    # tenant B forces tenant A to be the least-recently-used evictable bundle.
    second = client.get("/revenue-actions", headers=headers_b)
    assert second.status_code == 200, second.text
    assert second.json()["actions"] == 0
    assert tenant_app._service_registry is not None
    assert str(TENANT_A) not in tenant_app._service_registry.instances

    rebuilt = client.get("/revenue-actions", headers=headers_a)
    assert rebuilt.status_code == 200, rebuilt.text
    rebuilt_body = rebuilt.json()
    assert rebuilt_body["source_scores"]["tenant-upgrade-source"] == before_source
    assert rebuilt_body["lane_priorities"]["high_intent_lead_pack"] == before_lane
    assert rebuilt_body["actions"] == before_body["actions"]
    assert rebuilt_body["outcomes"] == before_body["outcomes"]
    assert str(TENANT_A) in tenant_app._service_registry.instances

    print(
        "TENANT_REVENUE_EVICTION_LEARNING_GO: tenant-owned outcome replay restored "
        "lane/source learning and execution state after forced bundle eviction"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
