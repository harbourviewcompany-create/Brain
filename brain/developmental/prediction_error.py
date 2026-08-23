from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ..domain import utcnow


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class PredictionRecord:
    statement: str
    predicted_value: float
    confidence: float
    source_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class PredictionError:
    prediction_id: UUID
    actual_value: float
    signed_error: float
    absolute_error: float
    surprise: float
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CalibrationTrace:
    prediction_id: UUID
    confidence_before: float
    confidence_after: float
    calibration_loss: float
    source_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentPressure:
    prediction_id: UUID
    pressure: float
    learning_priority: float
    reasons: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class PredictionErrorService:
    """Compute auditable surprise from a prediction and observed outcome."""

    def compute(self, prediction: PredictionRecord, actual_value: float) -> PredictionError:
        if not prediction.source_refs:
            raise ValueError("prediction error requires source traceability")
        signed = float(actual_value) - float(prediction.predicted_value)
        absolute = abs(signed)
        surprise = _clamp01(absolute) * (0.5 + 0.5 * _clamp01(prediction.confidence))
        return PredictionError(
            prediction_id=prediction.id,
            actual_value=float(actual_value),
            signed_error=signed,
            absolute_error=absolute,
            surprise=surprise,
        )


class CalibrationService:
    """Update confidence from observed error without deleting the prior state."""

    def update(self, prediction: PredictionRecord, error: PredictionError) -> CalibrationTrace:
        if error.prediction_id != prediction.id:
            raise ValueError("calibration error does not belong to prediction")
        confidence_before = _clamp01(prediction.confidence)
        calibration_loss = _clamp01(error.absolute_error)
        confidence_after = _clamp01(confidence_before * (1.0 - 0.5 * calibration_loss))
        return CalibrationTrace(
            prediction_id=prediction.id,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            calibration_loss=calibration_loss,
            source_refs=list(prediction.source_refs),
        )


class DevelopmentPressureService:
    """Convert error and unresolved cognitive debt into learning priority."""

    def score(
        self,
        error: PredictionError,
        *,
        contradiction_burden: float = 0.0,
        evidence_gap: float = 0.0,
        operator_intervention: float = 0.0,
    ) -> DevelopmentPressure:
        contradiction = _clamp01(contradiction_burden)
        gap = _clamp01(evidence_gap)
        intervention = _clamp01(operator_intervention)
        pressure = _clamp01(
            error.surprise * 0.55 + contradiction * 0.2 + gap * 0.2 + intervention * 0.05
        )
        reasons: list[str] = []
        if error.surprise > 0.25:
            reasons.append("prediction_error")
        if contradiction > 0.25:
            reasons.append("contradiction_burden")
        if gap > 0.25:
            reasons.append("evidence_gap")
        if intervention > 0.25:
            reasons.append("operator_intervention")
        return DevelopmentPressure(
            prediction_id=error.prediction_id,
            pressure=pressure,
            learning_priority=pressure,
            reasons=reasons or ["routine_calibration"],
        )
