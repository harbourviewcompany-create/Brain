"""PR #183 atomic scoring and warm-replica tenant execution verifier."""
from __future__ import annotations

import os
from uuid import UUID

import psycopg

from brain.adapters.revenue_store import PostgresRevenueStore
from brain.money_spine import (
    MoneySpineService,
    RevenueActionState,
    RevenueExecutionSpine,
    RevenueOutcomeType,
    RevenueSignal,
    ScoredOpportunity,
)
from brain.tenant_auth import TenantRole
from brain.tenant_context import trusted_tenant_context
from brain.tenant_runtime import tenant_context_scope

TENANT_A = UUID("cacacaca-caca-caca-caca-cacacacacaca")
TENANT_B = UUID("dbdbdbdb-dbdb-dbdb-dbdb-dbdbdbdbdbdb")
ACTOR_A = "replica-operator-a"
ACTOR_B = "replica-operator-b"
FAULT_SIGNAL = UUID("91919191-9191-9191-9191-919191919191")
FAULT_SCORE = UUID("92929292-9292-9292-9292-929292929292")


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def seed_tenants(admin_dsn: str) -> None:
    with psycopg.connect(admin_dsn) as conn:
        conn.execute(
            """
            insert into public.tenants (id, name, slug, status)
            values
              (%s, 'Replica Tenant A', 'replica-tenant-a', 'active'),
              (%s, 'Replica Tenant B', 'replica-tenant-b', 'active')
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
              role = excluded.role, status = excluded.status, removed_at = null
            """,
            (TENANT_A, ACTOR_A, TENANT_B, ACTOR_B),
        )
        conn.commit()


def signal(raw: str, source_id: str = "replica-source") -> RevenueSignal:
    return RevenueSignal(
        raw_signal=raw,
        source_id=source_id,
        money_lane_id="high_intent_lead_pack",
        evidence_refs=["https://example.test/replica"],
        named_buyer="Replica Buyer",
        decision_maker="Operations Lead",
        visible_pain="Urgent verified need",
        urgency_reason="Public urgent request",
        payment_path="Approved manual action",
        contact_channel="buyer@example.test",
        commercial_value=0.8,
        confidence=0.9,
        urgency=0.9,
        contactability=0.9,
        execution_difficulty=0.2,
        legal_access_risk=0.0,
        time_delay=0.1,
    )


def prove_atomic_rollback(admin_dsn: str) -> None:
    store = PostgresRevenueStore(dsn=admin_dsn)
    fault_signal = signal("fault-injected atomic rollback", "fault-source")
    fault_signal.id = FAULT_SIGNAL
    fault_score = ScoredOpportunity(
        signal_id=FAULT_SIGNAL,
        lane_id="high_intent_lead_pack",
        score=91.0,
        actionable=True,
        rejection_reasons=[],
        id=FAULT_SCORE,
    )
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute("drop trigger if exists brain_ci_fail_scored_insert on public.scored_revenue_opportunities")
        conn.execute("drop function if exists public.brain_ci_fail_scored_insert()")
        conn.execute(
            f"""
            create function public.brain_ci_fail_scored_insert() returns trigger
            language plpgsql as $$
            begin
              if new.id = '{FAULT_SCORE}'::uuid then
                raise exception 'ci injected scored-opportunity failure';
              end if;
              return new;
            end
            $$
            """
        )
        conn.execute(
            """
            create trigger brain_ci_fail_scored_insert
            before insert on public.scored_revenue_opportunities
            for each row execute function public.brain_ci_fail_scored_insert()
            """
        )
    try:
        try:
            store.save_signal_and_score(fault_signal, fault_score)
        except psycopg.Error as exc:
            assert "ci injected scored-opportunity failure" in str(exc)
        else:
            raise AssertionError("fault injection did not fail scored-opportunity insert")
        with psycopg.connect(admin_dsn) as conn:
            signal_count = conn.execute(
                "select count(*) from public.revenue_signals where id = %s",
                (FAULT_SIGNAL,),
            ).fetchone()[0]
            score_count = conn.execute(
                "select count(*) from public.scored_revenue_opportunities where id = %s",
                (FAULT_SCORE,),
            ).fetchone()[0]
        assert signal_count == 0, signal_count
        assert score_count == 0, score_count
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as conn:
            conn.execute("drop trigger if exists brain_ci_fail_scored_insert on public.scored_revenue_opportunities")
            conn.execute("drop function if exists public.brain_ci_fail_scored_insert()")
        store.close()
    print("REVENUE_SIGNAL_SCORE_ATOMIC_ROLLBACK_GO: injected score failure rolled back both audit rows")


def prove_two_replica_rls(admin_dsn: str) -> None:
    seed_tenants(admin_dsn)
    from apps.api import tenant_app

    if tenant_app._scoped_pool is None:
        raise AssertionError("canonical tenant scoped pool unavailable")
    context_a = trusted_tenant_context(
        tenant_id=TENANT_A, actor_id=ACTOR_A, roles=(TenantRole.OPERATOR,)
    )
    context_b = trusted_tenant_context(
        tenant_id=TENANT_B, actor_id=ACTOR_B, roles=(TenantRole.OPERATOR,)
    )

    with tenant_context_scope(context_a):
        store_a = tenant_app.TenantRevenueStore(pool=tenant_app._scoped_pool)
        store_b = tenant_app.TenantRevenueStore(pool=tenant_app._scoped_pool)
        replica_a = RevenueExecutionSpine(
            money=MoneySpineService(store=store_a), store=store_a
        )
        replica_b = RevenueExecutionSpine(
            money=MoneySpineService(store=store_b), store=store_b
        )
        assert replica_a.snapshot()["actions"] == 0
        assert replica_b.snapshot()["actions"] == 0

        _, _, action = replica_a.queue_action_from_signal(
            signal("action queued on already-warm replica A")
        )
        assert action.id not in replica_b.actions
        assert replica_b.get_action(action.id).id == action.id

        approved = replica_b.approve_action(action.id, approved_by=ACTOR_A)
        assert approved.state == RevenueActionState.APPROVED
        followup = replica_b.schedule_follow_up(
            action.id, script="replica B durable follow-up", delay_hours=24
        )
        outcome = replica_b.record_outcome(
            action.id,
            outcome_type=RevenueOutcomeType.PAID_CONVERSION,
            revenue=375.0,
            reply=True,
            meeting_booked=True,
            paid_conversion=True,
            legal_risk=0.0,
            operator_hours=1.0,
            lesson="warm replica B observed durable replica A action",
        )
        assert followup.action_id == action.id
        assert outcome.action_id == action.id
        assert replica_b.get_action(action.id).state == RevenueActionState.OUTCOME_LOGGED
        assert replica_a.get_action(action.id).state == RevenueActionState.OUTCOME_LOGGED
        snapshot_b = replica_b.snapshot()
        assert snapshot_b["actions"] == 1
        assert snapshot_b["followups"] == 1
        assert snapshot_b["outcomes"] == 1

    with tenant_context_scope(context_b):
        other_store = tenant_app.TenantRevenueStore(pool=tenant_app._scoped_pool)
        other_replica = RevenueExecutionSpine(
            money=MoneySpineService(store=other_store), store=other_store
        )
        assert other_replica.snapshot()["actions"] == 0
        try:
            other_replica.get_action(action.id)
        except KeyError:
            pass
        else:
            raise AssertionError("cross-tenant replica read exposed tenant A action")

    print(
        "TENANT_REVENUE_TWO_REPLICA_GO: warm replica B read, approved, followed up, "
        "and recorded an outcome for replica A's durable action; tenant B remained isolated"
    )


def main() -> int:
    admin_dsn = required_env("VERIFY_DATABASE_URL")
    required_env("DATABASE_URL")
    required_env("BRAIN_TENANT_CONTEXT_SECRET")
    required_env("BRAIN_API_KEY")
    if os.environ.get("BRAIN_TENANT_MODE") != "required":
        raise RuntimeError("BRAIN_TENANT_MODE=required is required")
    prove_atomic_rollback(admin_dsn)
    prove_two_replica_rls(admin_dsn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
