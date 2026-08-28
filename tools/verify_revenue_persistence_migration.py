"""Production-shaped verification for revenue scoring persistence migration 024.

Run against a disposable PostgreSQL database that has either the legacy pre-024
schema or migration 024 applied. This exercises the real psycopg adapter and
MoneySpineService rather than fake pools.
"""
from __future__ import annotations

import argparse
import os

from brain.adapters.revenue_store import PostgresRevenueStore
from brain.money_spine import MoneySpineService, RevenueSignal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect", choices=("pre024", "post024"), required=True)
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    store = PostgresRevenueStore(dsn)
    try:
        money = MoneySpineService(store=store)
        signal = RevenueSignal(
            raw_signal="Verified integration buyer is actively looking for a supplier",
            source_id="integration-source-key",
            money_lane_id="high_intent_lead_pack",
            evidence_refs=["https://example.test/integration-source"],
            named_buyer="Integration Buyer",
            visible_pain="Needs a qualified supplier now",
            contact_channel="buyer@example.test",
            commercial_value=0.8,
            confidence=0.9,
            urgency=0.8,
            contactability=0.9,
            execution_difficulty=0.2,
            legal_access_risk=0.0,
            time_delay=0.1,
            metadata={"verification": "migration-024-production-shaped"},
        )
        scored = money.score_signal(signal)
        if not scored.actionable:
            raise AssertionError(f"fixture unexpectedly rejected: {scored.rejection_reasons}")
        offer = money.package_offer(signal, scored)

        with store.pool.connection() as conn:
            signal_count = conn.execute(
                "select count(*) from public.revenue_signals where id = %s", (signal.id,)
            ).fetchone()[0]
            scored_count = conn.execute(
                "select count(*) from public.scored_revenue_opportunities where id = %s", (scored.id,)
            ).fetchone()[0]
            offer_count = conn.execute(
                "select count(*) from public.packaged_offers where id = %s", (offer.id,)
            ).fetchone()[0]

            if args.expect == "pre024":
                assert store._signal_audit_schema_is_ready() is False
                assert (signal_count, scored_count, offer_count) == (0, 0, 0)
                print("PRE024_GO: scoring succeeded and audit writes safely no-op on legacy UUID schema")
                return 0

            assert store._signal_audit_schema_is_ready() is True
            assert (signal_count, scored_count, offer_count) == (1, 1, 1)
            signal_keys = conn.execute(
                "select source_id, money_lane_id from public.revenue_signals where id = %s",
                (signal.id,),
            ).fetchone()
            scored_lane = conn.execute(
                "select money_lane_id from public.scored_revenue_opportunities where id = %s",
                (scored.id,),
            ).fetchone()[0]
            assert signal_keys == ("integration-source-key", "high_intent_lead_pack")
            assert scored_lane == "high_intent_lead_pack"
            print("POST024_GO: signal, score, and offer persisted with stable text keys")
            return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
