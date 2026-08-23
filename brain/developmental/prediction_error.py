from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class PredictionRecord:
    predicted_probability: float
    actual_outcome: float | None = None
    object_ref: str = ""
    source_refs: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class PredictionError:
    prediction_id: UUID
    absolute_error: float
    signed_error: float
    surprise: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CalibrationTrace:
    prediction_id: UUID
    prior_probability: float
    actual_outcome: float
    error_id: UUID
    preserved_source_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentPressure:
    target: str
    priority: float
    reason: str
    error_id: UUID
    audited_transition: str
    external_action_triggered: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class PredictionErrorService:
    predictions: list[PredictionRecord] = field(default_factory=list)
    errors: list[PredictionError] = field(default_factory=list)
    calibration: list[CalibrationTrace] = field(default_factory=list)
    pressures: list[DevelopmentPressure] = field(default_factory=list)

    def record_prediction(
        self,
        *,
        predicted_probability: float,
        object_ref: str,
        source_refs: list[str],
    ) -> PredictionRecord:
        if not 0.0 <= predicted_probability <= 1.0:
            raise ValueError("prediction_probability_out_of_range")
        if not source_refs:
            raise ValueError("prediction_requires_source_refs")
        record = PredictionRecord(
            predicted_probability=predicted_probability,
            object_ref=object_ref,
            source_refs=source_refs,
        )
        self.predictions.append(record)
        return record

    def resolve_prediction(
        self,
        prediction: PredictionRecord,
        *,
        actual_outcome: float,
        evidence_refs: list[str],
    ) -> tuple[PredictionError, CalibrationTrace]:
        if not 0.0 <= actual_outcome <= 1.0:
            raise ValueError("actual_outcome_out_of_range")
        if not evidence_refs:
            raise ValueError("prediction_resolution_requires_evidence")
        prediction.actual_outcome = actual_outcome
        signed = actual_outcome - prediction.predicted_probability
        absolute = abs(signed)
        error = PredictionError(
            prediction_id=prediction.id,
            absolute_error=absolute,
            signed_error=signed,
            surprise=absolute * (1.0 + abs(0.5 - prediction.predicted_probability)),
            evidence_refs=list(evidence_refs),
        )
        trace = CalibrationTrace(
            prediction_id=prediction.id,
            prior_probability=prediction.predicted_probability,
            actual_outcome=actual_outcome,
            error_id=error.id,
            preserved_source_refs=list(prediction.source_refs) + list(evidence_refs),
        )
        self.errors.append(error)
        self.calibration.append(trace)
        return error, trace

    def create_development_pressure(
        self,
        error: PredictionError,
        *,
        target: str,
        uncertainty: float,
    ) -> DevelopmentPressure:
        if not target:
            raise ValueError("development_pressure_requires_target")
        priority = min(1.0, max(0.0, error.absolute_error * (1.0 + max(uncertainty, 0.0))))
        pressure = DevelopmentPressure(
            target=target,
            priority=priority,
            reason="prediction_error",
            error_id=error.id,
            audited_transition="learning_priority.reweighted_by_prediction_error",
            external_action_triggered=False,
        )
        self.pressures.append(pressure)
        return pressure
