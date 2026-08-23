from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class ModelProfile:
    provider: str
    model: str
    task_strengths: dict[str, float]
    calibration: float = 0.5
    historical_accuracy: float = 0.5
    latency_score: float = 0.5
    cost_score: float = 0.5
    context_score: float = 0.5
    tool_score: float = 0.5
    enabled: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ModelRoute:
    task_type: str
    model_id: UUID
    score: float
    reasons: dict[str, float]
    escalation_required: bool


@dataclass(slots=True)
class ModelOutput:
    model_id: UUID
    content: str
    confidence: float
    evidence_refs: list[str]


@dataclass(slots=True)
class EnsembleAssessment:
    disagreement: float
    mean_confidence: float
    requires_adversarial_review: bool
    model_ids: list[UUID]


class ModelCortexRouter:
    """Route cognition to replaceable models using measured performance, not identity."""

    def __init__(self) -> None:
        self.models: dict[UUID, ModelProfile] = {}

    def register(self, profile: ModelProfile) -> ModelProfile:
        profile.calibration = _clamp01(profile.calibration)
        profile.historical_accuracy = _clamp01(profile.historical_accuracy)
        self.models[profile.id] = profile
        return profile

    def route(
        self,
        task_type: str,
        *,
        cost_priority: float = 0.5,
        latency_priority: float = 0.5,
        tool_required: bool = False,
        minimum_score: float = 0.25,
    ) -> ModelRoute:
        candidates: list[tuple[float, ModelProfile, dict[str, float]]] = []
        for model in self.models.values():
            if not model.enabled:
                continue
            task_fit = _clamp01(model.task_strengths.get(task_type, model.task_strengths.get("general", 0.0)))
            reasons = {
                "task_fit": task_fit,
                "historical_accuracy": _clamp01(model.historical_accuracy),
                "calibration": _clamp01(model.calibration),
                "context": _clamp01(model.context_score),
                "tools": _clamp01(model.tool_score),
                "cost": _clamp01(model.cost_score),
                "latency": _clamp01(model.latency_score),
            }
            score = (
                reasons["task_fit"] * 0.28
                + reasons["historical_accuracy"] * 0.22
                + reasons["calibration"] * 0.18
                + reasons["context"] * 0.08
                + reasons["tools"] * (0.12 if tool_required else 0.04)
                + reasons["cost"] * 0.12 * _clamp01(cost_priority)
                + reasons["latency"] * 0.12 * _clamp01(latency_priority)
            )
            candidates.append((score, model, reasons))
        if not candidates:
            raise LookupError("no enabled model can serve task")
        score, model, reasons = max(candidates, key=lambda item: (item[0], str(item[1].id)))
        return ModelRoute(
            task_type=task_type,
            model_id=model.id,
            score=score,
            reasons=reasons,
            escalation_required=score < minimum_score,
        )

    def assess_ensemble(self, outputs: list[ModelOutput]) -> EnsembleAssessment:
        if not outputs:
            raise ValueError("ensemble assessment requires outputs")
        confidences = [_clamp01(item.confidence) for item in outputs]
        mean = sum(confidences) / len(confidences)
        normalized_contents = {item.content.strip().lower() for item in outputs}
        content_disagreement = 0.0 if len(normalized_contents) == 1 else min(1.0, (len(normalized_contents) - 1) / len(outputs))
        confidence_spread = max(confidences) - min(confidences)
        disagreement = _clamp01(content_disagreement * 0.7 + confidence_spread * 0.3)
        return EnsembleAssessment(
            disagreement=disagreement,
            mean_confidence=mean,
            requires_adversarial_review=disagreement >= 0.35,
            model_ids=[item.model_id for item in outputs],
        )
