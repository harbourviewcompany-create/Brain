from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .domain import Outcome, utcnow


class PredictionStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Prediction:
    """Explicit forecast the Brain can later score against an Outcome."""

    statement: str
    expected_value: float
    confidence: float
    horizon: timedelta
    belief_id: UUID | None = None
    action_id: UUID | None = None
    edge_ids: list[UUID] = field(default_factory=list)
    source_keys: list[str] = field(default_factory=list)
    status: PredictionStatus = PredictionStatus.OPEN
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    resolve_by: datetime | None = None
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.resolve_by is None:
            self.resolve_by = self.created_at + self.horizon


@dataclass(slots=True)
class PredictionResolution:
    prediction: Prediction
    outcome: Outcome
    error: float
    signed_error: float
    reward_signal: float


class PredictionEngine:
    """Create and resolve predictions; error feeds attribution / learning."""

    def create(
        self,
        statement: str,
        *,
        expected_value: float,
        confidence: float = 0.5,
        horizon: timedelta | None = None,
        belief_id: UUID | None = None,
        action_id: UUID | None = None,
        edge_ids: list[UUID] | None = None,
        source_keys: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Prediction:
        return Prediction(
            statement=statement,
            expected_value=float(expected_value),
            confidence=max(0.0, min(1.0, float(confidence))),
            horizon=horizon or timedelta(days=7),
            belief_id=belief_id,
            action_id=action_id,
            edge_ids=list(edge_ids or []),
            source_keys=list(source_keys or []),
            metadata=dict(metadata or {}),
        )

    def resolve(self, prediction: Prediction, outcome: Outcome) -> PredictionResolution:
        if prediction.status is not PredictionStatus.OPEN:
            raise ValueError(f"prediction {prediction.id} is not open")
        signed = float(outcome.value_created) - float(prediction.expected_value)
        error = abs(signed)
        accuracy = max(0.0, 1.0 - min(1.0, error))
        reward_signal = accuracy * prediction.confidence
        if signed < 0:
            reward_signal = -reward_signal
        resolved = replace(
            prediction,
            status=PredictionStatus.RESOLVED,
            resolved_at=utcnow(),
        )
        return PredictionResolution(
            prediction=resolved,
            outcome=outcome,
            error=error,
            signed_error=signed,
            reward_signal=reward_signal,
        )

    def expire(self, prediction: Prediction, *, now: datetime | None = None) -> Prediction:
        now = now or utcnow()
        if prediction.status is not PredictionStatus.OPEN:
            return prediction
        if prediction.resolve_by and now >= prediction.resolve_by:
            return replace(prediction, status=PredictionStatus.EXPIRED, resolved_at=now)
        return prediction
