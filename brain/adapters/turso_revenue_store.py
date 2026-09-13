from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from ..money_spine import (
    AutomationReadiness,
    MoneyLane,
    OpportunityClass,
    RevenueActionState,
    RevenueExecutionAction,
    RevenueFollowUp,
    RevenueOutcomeLedgerEntry,
    RevenueOutcomeType,
)
from .turso import TursoDatabase, _dt, _iso, _json_dumps, _json_loads


class TursoRevenueStore:
    """libSQL equivalent of PostgresRevenueStore for the serverless runtime."""

    def __init__(self, db: TursoDatabase) -> None:
        self.db = db

    def load_lanes(self) -> dict[str, MoneyLane]:
        rows = self.db.fetchall(
            """
            SELECT lane_key,title,opportunity_class,packaged_offer,buyer_type,
                   seller_or_target_type,first_48_hour_action,price_low,price_high,
                   repeatability,fulfillment_difficulty,time_to_cash_days,
                   automation_readiness,legal_access_risk,priority_score
            FROM money_lanes
            """
        )
        return {str(row["lane_key"]): self._row_to_lane(row) for row in rows}

    @staticmethod
    def _row_to_lane(row) -> MoneyLane:
        return MoneyLane(
            lane_id=str(row["lane_key"]),
            title=str(row["title"]),
            opportunity_class=OpportunityClass(str(row["opportunity_class"])),
            packaged_offer=str(row["packaged_offer"]),
            buyer_type=str(row["buyer_type"]),
            seller_or_target_type=str(row["seller_or_target_type"]),
            source_targets=[],
            search_queries=[],
            first_48_hour_action=str(row["first_48_hour_action"]),
            price_low=float(row["price_low"]),
            price_high=float(row["price_high"]),
            repeatability=float(row["repeatability"]),
            fulfillment_difficulty=float(row["fulfillment_difficulty"]),
            time_to_cash_days=float(row["time_to_cash_days"]),
            automation_readiness=AutomationReadiness(str(row["automation_readiness"])),
            legal_access_risk=float(row["legal_access_risk"]),
            priority_score=float(row["priority_score"]),
        )

    def seed_lanes(self, lanes: list[MoneyLane]) -> None:
        now = _iso(datetime.now(timezone.utc))
        for lane in lanes:
            self.db.execute(
                """
                INSERT INTO money_lanes(
                    lane_key,title,opportunity_class,packaged_offer,buyer_type,
                    seller_or_target_type,first_48_hour_action,price_low,price_high,
                    repeatability,fulfillment_difficulty,time_to_cash_days,
                    automation_readiness,legal_access_risk,priority_score,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(lane_key) DO UPDATE SET title=excluded.title,
                    packaged_offer=excluded.packaged_offer,buyer_type=excluded.buyer_type,
                    seller_or_target_type=excluded.seller_or_target_type,
                    first_48_hour_action=excluded.first_48_hour_action,
                    price_low=excluded.price_low,price_high=excluded.price_high,
                    updated_at=excluded.updated_at
                """,
                (
                    lane.lane_id,
                    lane.title,
                    lane.opportunity_class.value,
                    lane.packaged_offer,
                    lane.buyer_type,
                    lane.seller_or_target_type,
                    lane.first_48_hour_action,
                    lane.price_low,
                    lane.price_high,
                    lane.repeatability,
                    lane.fulfillment_difficulty,
                    lane.time_to_cash_days,
                    lane.automation_readiness.value,
                    lane.legal_access_risk,
                    lane.priority_score,
                    now,
                ),
            )
        self.db.commit()

    def save_lane_priority(self, lane: MoneyLane) -> None:
        self.db.execute(
            "UPDATE money_lanes SET priority_score=?,updated_at=? WHERE lane_key=?",
            (lane.priority_score, _iso(datetime.now(timezone.utc)), lane.lane_id),
        )
        self.db.commit()

    def load_source_scores(self) -> dict[str, float]:
        return {
            str(row["source_id"]): float(row["score"])
            for row in self.db.fetchall("SELECT source_id,score FROM revenue_source_scores")
        }

    def save_source_score(self, source_id: str, score: float) -> None:
        self.db.execute(
            """
            INSERT INTO revenue_source_scores(source_id,score,updated_at) VALUES (?,?,?)
            ON CONFLICT(source_id) DO UPDATE SET score=excluded.score,updated_at=excluded.updated_at
            """,
            (source_id, score, _iso(datetime.now(timezone.utc))),
        )
        self.db.commit()

    def load_actions(self) -> dict[UUID, RevenueExecutionAction]:
        rows = self.db.fetchall("SELECT * FROM revenue_execution_actions")
        return {UUID(str(row["id"])): self._row_to_action(row) for row in rows}

    @staticmethod
    def _row_to_action(row) -> RevenueExecutionAction:
        return RevenueExecutionAction(
            id=UUID(str(row["id"])),
            opportunity_id=UUID(str(row["opportunity_id"])),
            offer_id=UUID(str(row["offer_id"])),
            lane_id=str(row["lane_id"]),
            source_id=str(row["source_id"]),
            action_type=str(row["action_type"]),
            target_contact=str(row["target_contact"]),
            proposal=str(row["proposal"]),
            evidence_refs=list(_json_loads(row.get("evidence_refs"), [])),
            approval_required=bool(row["approval_required"]),
            state=RevenueActionState(str(row["state"])),
            approved_by=row.get("approved_by"),
            manual_proof_ref=row.get("manual_proof_ref"),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
        )

    def save_action(self, action: RevenueExecutionAction) -> None:
        self.db.execute(
            """
            INSERT INTO revenue_execution_actions(
                id,opportunity_id,offer_id,lane_id,source_id,action_type,target_contact,
                proposal,evidence_refs,approval_required,state,approved_by,manual_proof_ref,
                created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET state=excluded.state,
                approved_by=excluded.approved_by,manual_proof_ref=excluded.manual_proof_ref,
                updated_at=excluded.updated_at
            """,
            (
                str(action.id),
                str(action.opportunity_id),
                str(action.offer_id),
                action.lane_id,
                action.source_id,
                action.action_type,
                action.target_contact,
                action.proposal,
                _json_dumps(list(action.evidence_refs)),
                int(action.approval_required),
                action.state.value,
                action.approved_by,
                action.manual_proof_ref,
                _iso(action.created_at),
                _iso(action.updated_at),
            ),
        )
        self.db.commit()

    def load_followups(self) -> dict[UUID, RevenueFollowUp]:
        rows = self.db.fetchall("SELECT * FROM revenue_followups")
        return {UUID(str(row["id"])): self._row_to_followup(row) for row in rows}

    @staticmethod
    def _row_to_followup(row) -> RevenueFollowUp:
        return RevenueFollowUp(
            id=UUID(str(row["id"])),
            action_id=UUID(str(row["action_id"])),
            due_at=_dt(row["due_at"]),
            script=str(row["script"]),
            state=str(row["state"]),
            completed_at=_dt(row["completed_at"]) if row.get("completed_at") else None,
        )

    def save_followup(self, followup: RevenueFollowUp) -> None:
        self.db.execute(
            """
            INSERT INTO revenue_followups(id,action_id,due_at,script,state,completed_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET state=excluded.state,completed_at=excluded.completed_at
            """,
            (
                str(followup.id),
                str(followup.action_id),
                _iso(followup.due_at),
                followup.script,
                followup.state,
                _iso(followup.completed_at) if followup.completed_at else None,
            ),
        )
        self.db.commit()

    def load_outcomes(self) -> dict[UUID, RevenueOutcomeLedgerEntry]:
        rows = self.db.fetchall("SELECT * FROM revenue_outcome_ledger")
        return {UUID(str(row["id"])): self._row_to_outcome(row) for row in rows}

    @staticmethod
    def _row_to_outcome(row) -> RevenueOutcomeLedgerEntry:
        return RevenueOutcomeLedgerEntry(
            id=UUID(str(row["id"])),
            action_id=UUID(str(row["action_id"])),
            lane_id=str(row["lane_id"]),
            source_id=str(row["source_id"]),
            outcome_type=RevenueOutcomeType(str(row["outcome_type"])),
            revenue=float(row["revenue"]),
            reply=bool(row["reply"]),
            meeting_booked=bool(row["meeting_booked"]),
            paid_conversion=bool(row["paid_conversion"]),
            legal_risk=float(row["legal_risk"]),
            operator_hours=float(row["operator_hours"]),
            lesson=str(row["lesson"]),
            created_at=_dt(row["created_at"]),
        )

    def save_outcome(self, entry: RevenueOutcomeLedgerEntry) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO revenue_outcome_ledger(
                id,action_id,lane_id,source_id,outcome_type,revenue,reply,meeting_booked,
                paid_conversion,legal_risk,operator_hours,lesson,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                str(entry.id),
                str(entry.action_id),
                entry.lane_id,
                entry.source_id,
                entry.outcome_type.value,
                entry.revenue,
                int(entry.reply),
                int(entry.meeting_booked),
                int(entry.paid_conversion),
                entry.legal_risk,
                entry.operator_hours,
                entry.lesson,
                _iso(entry.created_at),
            ),
        )
        self.db.commit()
