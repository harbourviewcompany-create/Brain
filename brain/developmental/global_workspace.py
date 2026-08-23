from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ..domain import utcnow


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class WorkspaceItem:
    kind: str
    content: str
    evidence_refs: list[str]
    salience: float = 0.5
    urgency: float = 0.0
    uncertainty: float = 0.0
    contradiction: float = 0.0
    expected_value: float = 0.0
    noise_probability: float = 0.0
    operator_burden: float = 0.0
    intended_consumers: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class AttentionCoalition:
    winner_ids: list[UUID]
    winner_scores: dict[str, float]
    suppressed_ids: list[UUID]
    suppression_reasons: dict[str, str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class SuppressionEvent:
    item_id: UUID
    winning_item_ids: list[UUID]
    reason: str
    score: float
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class BroadcastEvent:
    coalition_id: UUID
    item_ids: list[UUID]
    evidence_refs: list[str]
    consumers: list[str]
    suppressed_item_ids: list[UUID]
    consciousness_claim: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class WorkspaceCompetitionService:
    """Finite attention market with explicit suppression evidence."""

    def score(self, item: WorkspaceItem) -> float:
        if not item.evidence_refs:
            return 0.0
        positive = (
            _clamp01(item.salience) * 0.22
            + _clamp01(item.urgency) * 0.17
            + _clamp01(item.uncertainty) * 0.13
            + _clamp01(item.contradiction) * 0.17
            + _clamp01(item.expected_value) * 0.21
        )
        penalty = _clamp01(item.noise_probability) * 0.06 + _clamp01(item.operator_burden) * 0.04
        return max(0.0, min(1.0, positive - penalty))

    def compete(
        self, items: list[WorkspaceItem], *, capacity: int = 1
    ) -> tuple[AttentionCoalition, list[SuppressionEvent]]:
        if capacity < 1:
            raise ValueError("workspace capacity must be positive")
        ranked = sorted(items, key=lambda item: (self.score(item), str(item.id)), reverse=True)
        winners = [item for item in ranked if item.evidence_refs][:capacity]
        suppressed = [item for item in ranked if item not in winners]
        winner_ids = [item.id for item in winners]
        coalition = AttentionCoalition(
            winner_ids=winner_ids,
            winner_scores={str(item.id): self.score(item) for item in winners},
            suppressed_ids=[item.id for item in suppressed],
            suppression_reasons={
                str(item.id): "lower_attention_bid" if item.evidence_refs else "missing_evidence"
                for item in suppressed
            },
        )
        events = [
            SuppressionEvent(
                item_id=item.id,
                winning_item_ids=winner_ids,
                reason=coalition.suppression_reasons[str(item.id)],
                score=self.score(item),
            )
            for item in suppressed
        ]
        return coalition, events


class BroadcastService:
    """Broadcast winning contents to named consumers without consciousness claims."""

    def broadcast(
        self,
        coalition: AttentionCoalition,
        items: list[WorkspaceItem],
        *,
        consumers: list[str] | None = None,
    ) -> BroadcastEvent:
        by_id = {item.id: item for item in items}
        winners = [by_id[item_id] for item_id in coalition.winner_ids if item_id in by_id]
        if not winners:
            raise ValueError("workspace broadcast requires at least one winning item")
        evidence = sorted({ref for item in winners for ref in item.evidence_refs})
        if not evidence:
            raise ValueError("workspace broadcast requires evidence")
        resolved_consumers = sorted(
            set(consumers or [consumer for item in winners for consumer in item.intended_consumers])
        )
        if not resolved_consumers:
            raise ValueError("workspace broadcast must record consuming modules")
        return BroadcastEvent(
            coalition_id=coalition.id,
            item_ids=[item.id for item in winners],
            evidence_refs=evidence,
            consumers=resolved_consumers,
            suppressed_item_ids=list(coalition.suppressed_ids),
            consciousness_claim=False,
        )
