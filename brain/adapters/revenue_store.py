"""Durable persistence for MoneySpineService and RevenueExecutionSpine.

The store persists learned lane/source state, the approval-gated execution
ledger, and (once migration 025 is present) the signal/scoring/offer audit
trail. Signal-audit writes are capability-gated so code can run safely on a
deployment whose migration ceiling is still below 025 even though migration
006 already created those tables with the legacy UUID key layout.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

try:
    from psycopg import errors as psycopg_errors
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover - exercised only without psycopg installed
    psycopg_errors = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc,assignment]

try:
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    dict_row = None

from ..money_spine import (
    AutomationReadiness,
    MoneyLane,
    OpportunityClass,
    PackagedOffer,
    RevenueActionState,
    RevenueExecutionAction,
    RevenueFollowUp,
    RevenueOutcomeLedgerEntry,
    RevenueOutcomeType,
    RevenueSignal,
    ScoredOpportunity,
)

_UndefinedTable: tuple[type[BaseException], ...] = (
    (psycopg_errors.UndefinedTable,) if psycopg_errors is not None else ()
)


class PostgresRevenueStore:
    """Load/save adapter over the money-spine and revenue-execution tables."""

    def __init__(self, dsn: str | None = None, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and ConnectionPool is Any:
            raise RuntimeError("PostgreSQL support requires psycopg dependencies")
        if pool is None and not dsn:
            raise ValueError("dsn_or_pool_required")
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)
        self._signal_audit_schema_ready: bool | None = None

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    # --- money lanes -----------------------------------------------------

    def load_lanes(self) -> dict[str, MoneyLane]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select lane_key, title, opportunity_class, packaged_offer, buyer_type,
                       seller_or_target_type, first_48_hour_action, price_low, price_high,
                       repeatability, fulfillment_difficulty, time_to_cash_days,
                       automation_readiness, legal_access_risk, priority_score
                from public.money_lanes
                """
            )
            return {row["lane_key"]: self._row_to_lane(row) for row in cur.fetchall()}

    @staticmethod
    def _row_to_lane(row: dict[str, Any]) -> MoneyLane:
        return MoneyLane(
            lane_id=row["lane_key"],
            title=row["title"],
            opportunity_class=OpportunityClass(row["opportunity_class"]),
            packaged_offer=row["packaged_offer"],
            buyer_type=row["buyer_type"],
            seller_or_target_type=row["seller_or_target_type"],
            source_targets=[],
            search_queries=[],
            first_48_hour_action=row["first_48_hour_action"],
            price_low=row["price_low"],
            price_high=row["price_high"],
            repeatability=row["repeatability"],
            fulfillment_difficulty=row["fulfillment_difficulty"],
            time_to_cash_days=row["time_to_cash_days"],
            automation_readiness=AutomationReadiness(row["automation_readiness"]),
            legal_access_risk=row["legal_access_risk"],
            priority_score=row["priority_score"],
        )

    def seed_lanes(self, lanes: list[MoneyLane]) -> None:
        with self.pool.connection() as conn:
            for lane in lanes:
                conn.execute(
                    """
                    insert into public.money_lanes (
                        lane_key, title, opportunity_class, packaged_offer, buyer_type,
                        seller_or_target_type, first_48_hour_action, price_low, price_high,
                        repeatability, fulfillment_difficulty, time_to_cash_days,
                        automation_readiness, legal_access_risk, priority_score
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (lane_key) do update set
                        title = excluded.title,
                        packaged_offer = excluded.packaged_offer,
                        buyer_type = excluded.buyer_type,
                        seller_or_target_type = excluded.seller_or_target_type,
                        first_48_hour_action = excluded.first_48_hour_action,
                        price_low = excluded.price_low,
                        price_high = excluded.price_high,
                        updated_at = now()
                    """,
                    (
                        lane.lane_id, lane.title, lane.opportunity_class.value, lane.packaged_offer,
                        lane.buyer_type, lane.seller_or_target_type, lane.first_48_hour_action,
                        lane.price_low, lane.price_high, lane.repeatability, lane.fulfillment_difficulty,
                        lane.time_to_cash_days, lane.automation_readiness.value, lane.legal_access_risk,
                        lane.priority_score,
                    ),
                )
            conn.commit()

    def save_lane_priority(self, lane: MoneyLane) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "update public.money_lanes set priority_score = %s, updated_at = now() where lane_key = %s",
                (lane.priority_score, lane.lane_id),
            )
            conn.commit()

    # --- source reliability scores ----------------------------------------

    def load_source_scores(self) -> dict[str, float]:
        try:
            with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute("select source_id, score from public.revenue_source_scores")
                return {row["source_id"]: float(row["score"]) for row in cur.fetchall()}
        except _UndefinedTable:
            return {}

    def save_source_score(self, source_id: str, score: float) -> None:
        try:
            with self.pool.connection() as conn:
                conn.execute(
                    """
                    insert into public.revenue_source_scores (source_id, score, updated_at)
                    values (%s, %s, now())
                    on conflict (source_id) do update set score = excluded.score, updated_at = now()
                    """,
                    (source_id, score),
                )
                conn.commit()
        except _UndefinedTable:
            pass

    # --- revenue execution actions -----------------------------------------

    def load_actions(self) -> dict[UUID, RevenueExecutionAction]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, opportunity_id, offer_id, lane_id, source_id, action_type,
                       target_contact, proposal, evidence_refs, approval_required, state,
                       approved_by, manual_proof_ref, created_at, updated_at
                from public.revenue_execution_actions
                """
            )
            return {row["id"]: self._row_to_action(row) for row in cur.fetchall()}

    @staticmethod
    def _row_to_action(row: dict[str, Any]) -> RevenueExecutionAction:
        return RevenueExecutionAction(
            id=row["id"],
            opportunity_id=row["opportunity_id"],
            offer_id=row["offer_id"],
            lane_id=row["lane_id"],
            source_id=row["source_id"],
            action_type=row["action_type"],
            target_contact=row["target_contact"],
            proposal=row["proposal"],
            evidence_refs=list(row["evidence_refs"] or []),
            approval_required=row["approval_required"],
            state=RevenueActionState(row["state"]),
            approved_by=row["approved_by"],
            manual_proof_ref=row["manual_proof_ref"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def save_action(self, action: RevenueExecutionAction) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.revenue_execution_actions (
                    id, opportunity_id, offer_id, lane_id, source_id, action_type,
                    target_contact, proposal, evidence_refs, approval_required, state,
                    approved_by, manual_proof_ref, created_at, updated_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                    state = excluded.state,
                    approved_by = excluded.approved_by,
                    manual_proof_ref = excluded.manual_proof_ref,
                    updated_at = excluded.updated_at
                """,
                (
                    action.id, action.opportunity_id, action.offer_id, action.lane_id, action.source_id,
                    action.action_type, action.target_contact, action.proposal,
                    Jsonb(list(action.evidence_refs)), action.approval_required, action.state.value,
                    action.approved_by, action.manual_proof_ref, action.created_at, action.updated_at,
                ),
            )
            conn.commit()

    # --- follow-ups ---------------------------------------------------------

    def load_followups(self) -> dict[UUID, RevenueFollowUp]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "select id, action_id, due_at, script, state, completed_at from public.revenue_followups"
            )
            return {row["id"]: self._row_to_followup(row) for row in cur.fetchall()}

    @staticmethod
    def _row_to_followup(row: dict[str, Any]) -> RevenueFollowUp:
        return RevenueFollowUp(
            id=row["id"],
            action_id=row["action_id"],
            due_at=row["due_at"],
            script=row["script"],
            state=row["state"],
            completed_at=row["completed_at"],
        )

    def save_followup(self, followup: RevenueFollowUp) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.revenue_followups (id, action_id, due_at, script, state, completed_at)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                    state = excluded.state,
                    completed_at = excluded.completed_at
                """,
                (followup.id, followup.action_id, followup.due_at, followup.script,
                 followup.state, followup.completed_at),
            )
            conn.commit()

    # --- outcome ledger -------------------------------------------------

    def load_outcomes(self) -> dict[UUID, RevenueOutcomeLedgerEntry]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, action_id, lane_id, source_id, outcome_type, revenue, reply,
                       meeting_booked, paid_conversion, legal_risk, operator_hours, lesson, created_at
                from public.revenue_outcome_ledger
                """
            )
            return {row["id"]: self._row_to_outcome(row) for row in cur.fetchall()}

    @staticmethod
    def _row_to_outcome(row: dict[str, Any]) -> RevenueOutcomeLedgerEntry:
        return RevenueOutcomeLedgerEntry(
            id=row["id"],
            action_id=row["action_id"],
            lane_id=row["lane_id"],
            source_id=row["source_id"],
            outcome_type=RevenueOutcomeType(row["outcome_type"]),
            revenue=float(row["revenue"]),
            reply=row["reply"],
            meeting_booked=row["meeting_booked"],
            paid_conversion=row["paid_conversion"],
            legal_risk=float(row["legal_risk"]),
            operator_hours=float(row["operator_hours"]),
            lesson=row["lesson"],
            created_at=row["created_at"],
        )

    def save_outcome(self, entry: RevenueOutcomeLedgerEntry) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.revenue_outcome_ledger (
                    id, action_id, lane_id, source_id, outcome_type, revenue, reply,
                    meeting_booked, paid_conversion, legal_risk, operator_hours, lesson, created_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    entry.id, entry.action_id, entry.lane_id, entry.source_id, entry.outcome_type.value,
                    entry.revenue, entry.reply, entry.meeting_booked, entry.paid_conversion,
                    entry.legal_risk, entry.operator_hours, entry.lesson, entry.created_at,
                ),
            )
            conn.commit()

    # --- signal scoring audit trail -----------------------------------------

    def _signal_audit_schema_is_ready(self) -> bool:
        """Return true only for migration-025-compatible text-key columns.

        Migration 006 already creates all three audit tables, so catching
        UndefinedTable cannot distinguish a pre-025 deployment from the fixed
        schema. Inspecting the actual column types fails closed on the legacy
        UUID layout and prevents scoring from crashing below the migration ceiling.
        """
        cached = getattr(self, "_signal_audit_schema_ready", None)
        if cached is not None:
            return cached
        try:
            with self.pool.connection() as conn:
                row = conn.execute(
                    """
                    select count(*)
                    from information_schema.columns
                    where table_schema = 'public'
                      and data_type = 'text'
                      and (
                        (table_name = 'revenue_signals' and column_name in ('source_id', 'money_lane_id'))
                        or (table_name = 'scored_revenue_opportunities' and column_name = 'money_lane_id')
                      )
                    """
                ).fetchone()
            ready = bool(row and int(row[0]) == 3)
        except _UndefinedTable:
            ready = False
        self._signal_audit_schema_ready = ready
        return ready

    def save_signal(self, signal: RevenueSignal) -> None:
        if not self._signal_audit_schema_is_ready():
            return
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.revenue_signals (
                    id, money_lane_id, source_id, raw_signal, named_buyer, named_seller,
                    decision_maker, visible_pain, urgency_reason, payment_path, contact_channel,
                    evidence_refs, commercial_value, confidence, urgency, contactability,
                    execution_difficulty, legal_access_risk, time_delay, metadata
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    signal.id, signal.money_lane_id, signal.source_id, signal.raw_signal,
                    signal.named_buyer, signal.named_seller, signal.decision_maker,
                    signal.visible_pain, signal.urgency_reason, signal.payment_path,
                    signal.contact_channel, Jsonb(list(signal.evidence_refs)),
                    signal.commercial_value, signal.confidence, signal.urgency,
                    signal.contactability, signal.execution_difficulty, signal.legal_access_risk,
                    signal.time_delay, Jsonb(dict(signal.metadata)),
                ),
            )
            conn.commit()

    def save_scored_opportunity(self, scored: ScoredOpportunity) -> None:
        if not self._signal_audit_schema_is_ready():
            return
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.scored_revenue_opportunities (
                    id, revenue_signal_id, money_lane_id, score, actionable,
                    rejection_reasons, next_action
                ) values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    scored.id, scored.signal_id, scored.lane_id, scored.score, scored.actionable,
                    Jsonb(list(scored.rejection_reasons)), scored.next_action,
                ),
            )
            conn.commit()

    def save_offer(self, offer: PackagedOffer) -> None:
        if not self._signal_audit_schema_is_ready():
            return
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.packaged_offers (
                    id, scored_opportunity_id, title, offer_name, buyer_type, target_contact,
                    price_low, price_high, evidence_refs, outreach_script, follow_up_script,
                    approval_required
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    offer.id, offer.opportunity_id, offer.title, offer.offer_name, offer.buyer_type,
                    offer.target_contact, offer.price_low, offer.price_high,
                    Jsonb(list(offer.evidence_refs)), offer.outreach_script, offer.follow_up_script,
                    offer.approval_required,
                ),
            )
            conn.commit()
