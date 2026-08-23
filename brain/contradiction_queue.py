from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from .domain import utcnow


class ContradictionStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    USER_DECISION_REQUIRED = "user_decision_required"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


@dataclass(slots=True)
class ContradictionReviewItem:
    belief_id: str
    supporting_claim: str
    contradicting_claim: str
    source_ids: list[str]
    severity: float
    status: ContradictionStatus = ContradictionStatus.OPEN
    review_required: bool = True
    resolution: str | None = None
    resolution_source: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


class ContradictionReviewService:
    """Preserves conflicts as reviewable objects instead of deleting one side."""

    def __init__(self) -> None:
        self.items: dict[UUID, ContradictionReviewItem] = {}

    def create_review_item(
        self,
        *,
        belief_id: str,
        supporting_claim: str,
        contradicting_claim: str,
        source_ids: list[str],
        severity: float,
    ) -> ContradictionReviewItem:
        if not supporting_claim or not contradicting_claim:
            raise ValueError("Both sides of a contradiction must be preserved.")
        if not source_ids:
            raise ValueError("Contradiction review requires source provenance.")
        item = ContradictionReviewItem(
            belief_id=belief_id,
            supporting_claim=supporting_claim,
            contradicting_claim=contradicting_claim,
            source_ids=list(source_ids),
            severity=max(0.0, min(1.0, severity)),
        )
        self.items[item.id] = item
        return item

    def require_user_decision(self, item_id: UUID) -> ContradictionReviewItem:
        item = self.items[item_id]
        updated = ContradictionReviewItem(
            belief_id=item.belief_id,
            supporting_claim=item.supporting_claim,
            contradicting_claim=item.contradicting_claim,
            source_ids=item.source_ids,
            severity=item.severity,
            status=ContradictionStatus.USER_DECISION_REQUIRED,
            review_required=True,
            resolution=item.resolution,
            resolution_source=item.resolution_source,
            id=item.id,
            created_at=item.created_at,
        )
        self.items[item_id] = updated
        return updated

    def resolve(
        self,
        item_id: UUID,
        *,
        resolution: str,
        resolution_source: str,
    ) -> ContradictionReviewItem:
        if resolution_source == "agent_preference":
            raise ValueError("Agents may not resolve contradictions by preference.")
        item = self.items[item_id]
        updated = ContradictionReviewItem(
            belief_id=item.belief_id,
            supporting_claim=item.supporting_claim,
            contradicting_claim=item.contradicting_claim,
            source_ids=item.source_ids,
            severity=item.severity,
            status=ContradictionStatus.RESOLVED,
            review_required=False,
            resolution=resolution,
            resolution_source=resolution_source,
            id=item.id,
            created_at=item.created_at,
        )
        self.items[item_id] = updated
        return updated

    def unresolved(self) -> list[ContradictionReviewItem]:
        return [
            item
            for item in self.items.values()
            if item.status not in {ContradictionStatus.RESOLVED, ContradictionStatus.SUPERSEDED}
        ]
