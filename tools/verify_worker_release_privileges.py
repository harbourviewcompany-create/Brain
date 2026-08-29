"""Production-shaped verification for migration 026 trusted-worker privileges.

This verifier is intended only for an isolated PostgreSQL database. It uses
separate migrator/admin, API-runtime, and trusted-worker credentials supplied by
the caller and proves that the post-tenant-release worker stays PostgreSQL-backed
instead of silently degrading connector or revenue state to memory.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg
from psycopg_pool import ConnectionPool

from brain.connectors.protocol import (
    AccessDisposition,
    ConnectorKind,
    ConnectorSource,
    RawObservationItem,
)
from brain.connectors.store import PostgresConnectorRegistry
from brain.money_spine import RevenueActionState, RevenueSignal
from brain.tenant_runtime import require_safe_runtime_role


CONNECTOR_KEY = "worker-release-connector"
CONNECTOR_HASH = "worker-release-connector-content-v1"
SOURCE_KEY = "worker-release-revenue-source"
LANE_KEY = "high_intent_lead_pack"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _has_privilege(conn: psycopg.Connection, table: str, privileges: str) -> bool:
    row = conn.execute(
        "select has_table_privilege(current_user, %s, %s)",
        (f"public.{table}", privileges),
    ).fetchone()
    return bool(row and row[0])


def verify_role_boundary(runtime_dsn: str, worker_dsn: str) -> None:
    connector_tables = (
        "source_connector_runtime_state",
        "source_connector_ingestion_runs",
        "source_connector_observations",
    )
    worker_global_tables = ("money_lanes", "revenue_source_scores")

    with psycopg.connect(worker_dsn, autocommit=True) as conn:
        require_safe_runtime_role(conn, require_trusted_service=True)
        for table in connector_tables:
            if not _has_privilege(conn, table, "SELECT,INSERT,UPDATE"):
                raise AssertionError(f"trusted worker lacks connector DML: {table}")
        for table in worker_global_tables:
            if not _has_privilege(conn, table, "SELECT,INSERT,UPDATE"):
                raise AssertionError(f"trusted worker lacks system revenue DML: {table}")

    with psycopg.connect(runtime_dsn, autocommit=True) as conn:
        require_safe_runtime_role(conn, require_trusted_service=False)
        for table in (*connector_tables, *worker_global_tables):
            if _has_privilege(conn, table, "SELECT"):
                raise AssertionError(f"ordinary API runtime unexpectedly reads worker-only table: {table}")

    print("WORKER_ROLE_BOUNDARY_GO: trusted worker has required DML; ordinary API role remains excluded")


def verify_connector_runtime(worker_dsn: str, admin_dsn: str) -> None:
    pool = ConnectionPool(conninfo=worker_dsn, min_size=1, max_size=2, open=True)
    try:
        registry = PostgresConnectorRegistry(pool, lease_owner="worker-release-verifier")
        if not registry.available():
            raise AssertionError("migration 024 connector registry is not available to trusted worker")

        source = registry.upsert(
            ConnectorSource(
                source_key=CONNECTOR_KEY,
                name="Worker Release Connector",
                url="https://example.test/worker-release-feed",
                kind=ConnectorKind.HTTP_TEXT,
                access=AccessDisposition.ALLOWED,
                refresh_seconds=30,
            )
        )
        claimed = registry.claim_due_sources(limit=10)
        claimed_source = next((item for item in claimed if item.source_key == CONNECTOR_KEY), None)
        if claimed_source is None:
            raise AssertionError("trusted worker could not claim its durable connector source")

        run_id = registry.start_ingestion_run(claimed_source)
        retrieved_at = datetime.now(timezone.utc)
        receipt = registry.record_fetched_item(
            claimed_source,
            RawObservationItem(
                title="Worker release privilege proof",
                content="Durable connector write through constrained trusted worker",
                claim="migration 026 grants the worker connector persistence path",
                source_url="https://example.test/worker-release-item",
                item_id="worker-release-item-1",
                content_hash=CONNECTOR_HASH,
                observed_at=retrieved_at,
                confidence=0.9,
            ),
            retrieved_at=retrieved_at,
            ingestion_run_id=run_id,
        )
        if receipt.observation_id is None or not receipt.should_enqueue:
            raise AssertionError("trusted worker connector observation was not durably captured")
        registry.finish_ingestion_run(
            run_id,
            status="success",
            retrieved_at=retrieved_at,
            fetched_count=1,
            enqueued_count=0,
            deduped_count=0,
            http_status=200,
            duration_ms=1.0,
            error_message=None,
        )
        registry.mark_fetch(CONNECTOR_KEY, success=True)
        if registry.seen_count() < 1:
            raise AssertionError("trusted worker cannot read back durable connector observations")
    finally:
        pool.close()

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        row = conn.execute(
            """
            select s.tenant_id, r.tenant_id, o.tenant_id, r.status, o.content_hash
            from public.source_connector_runtime_state s
            join public.source_connector_ingestion_runs r on r.source_id = s.id
            join public.source_connector_observations o on o.source_id = s.id
            where s.source_key = %s and o.content_hash = %s
            """,
            (CONNECTOR_KEY, CONNECTOR_HASH),
        ).fetchone()
        if not row:
            raise AssertionError("admin verification could not find connector persistence rows")
        if row[0] is not None or row[1] is not None or row[2] is not None:
            raise AssertionError("system worker connector rows were unexpectedly tenant reassigned")
        if str(row[3]) != "success" or str(row[4]) != CONNECTOR_HASH:
            raise AssertionError(f"unexpected durable connector state: {row}")

    print("WORKER_CONNECTOR_PERSISTENCE_GO: constrained worker selected, claimed, wrote, updated, and read durable connector state")


def _signal() -> RevenueSignal:
    return RevenueSignal(
        raw_signal="Verified worker release buyer needs a supplier",
        source_id=SOURCE_KEY,
        money_lane_id=LANE_KEY,
        evidence_refs=["https://example.test/worker-release-evidence"],
        named_buyer="Worker Release Buyer",
        decision_maker="Operations Lead",
        visible_pain="Needs a qualified supplier now",
        urgency_reason="Time-sensitive verified requirement",
        payment_path="Approval-gated manual commercial action",
        contact_channel="buyer@example.test",
        commercial_value=0.8,
        confidence=0.9,
        urgency=0.9,
        contactability=0.9,
        execution_difficulty=0.2,
        legal_access_risk=0.0,
        time_delay=0.1,
        metadata={"verification": "worker-release-privileges-026"},
    )


def verify_worker_revenue(worker_dsn: str, admin_dsn: str) -> None:
    from apps.worker import main as worker_main

    worker_main._verified_worker_dsn = None
    verified = worker_main.worker_database_url()
    if verified != worker_dsn:
        raise AssertionError("worker_database_url did not select BRAIN_WORKER_DATABASE_URL")

    spine = worker_main.build_revenue_spine()
    if spine.store is None:
        raise AssertionError("worker revenue spine silently fell back to in-memory storage")

    scored, offer, action = spine.queue_action_from_signal(_signal())
    if not scored.actionable:
        raise AssertionError(f"worker verification signal unexpectedly rejected: {scored.rejection_reasons}")
    if action.state != RevenueActionState.APPROVAL_REQUIRED or not action.approval_required:
        raise AssertionError("worker revenue action bypassed approval-required state")

    # Exercise the two system/global tables that previously made worker-store
    # construction fail under the constrained role. No external action is sent.
    spine.money.apply_outcome_learning(
        LANE_KEY,
        SOURCE_KEY,
        revenue=100.0,
        reply=True,
        legal_risk=0.0,
        operator_hours=0.5,
    )
    source_scores = spine.store.load_source_scores()
    if SOURCE_KEY not in source_scores:
        raise AssertionError("trusted worker source reliability update was not durable")

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        rows = {
            "signal": conn.execute(
                "select tenant_id from public.revenue_signals where id = %s", (scored.signal_id,)
            ).fetchone(),
            "score": conn.execute(
                "select tenant_id from public.scored_revenue_opportunities where id = %s", (scored.id,)
            ).fetchone(),
            "offer": conn.execute(
                "select tenant_id from public.packaged_offers where id = %s", (offer.id,)
            ).fetchone(),
            "action": conn.execute(
                "select tenant_id, state, approval_required from public.revenue_execution_actions where id = %s",
                (action.id,),
            ).fetchone(),
        }
        if any(value is None for value in rows.values()):
            raise AssertionError(f"worker revenue persistence row missing: {rows}")
        if rows["signal"][0] is not None or rows["score"][0] is not None or rows["offer"][0] is not None:
            raise AssertionError("system worker scoring rows were unexpectedly tenant reassigned")
        if rows["action"][0] is not None:
            raise AssertionError("system worker action was unexpectedly tenant reassigned")
        if str(rows["action"][1]) != RevenueActionState.APPROVAL_REQUIRED.value or not rows["action"][2]:
            raise AssertionError("persisted worker action is not approval-gated")

    print("WORKER_REVENUE_PERSISTENCE_GO: constrained worker remained PostgreSQL-backed and persisted approval-gated revenue state")


def main() -> int:
    admin_dsn = _required_env("VERIFY_DATABASE_URL")
    runtime_dsn = _required_env("DATABASE_URL")
    worker_dsn = _required_env("BRAIN_WORKER_DATABASE_URL")
    if os.environ.get("BRAIN_TENANT_MODE", "").strip().lower() != "required":
        raise RuntimeError("BRAIN_TENANT_MODE=required is required")

    verify_role_boundary(runtime_dsn, worker_dsn)
    verify_connector_runtime(worker_dsn, admin_dsn)
    verify_worker_revenue(worker_dsn, admin_dsn)
    print("WORKER_RELEASE_PRIVILEGES_GO: migration 026 closes the constrained-worker production-release gap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())