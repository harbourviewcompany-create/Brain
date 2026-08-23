from __future__ import annotations

from dataclasses import dataclass, fields
from enum import IntEnum


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class DevelopmentalStage(IntEnum):
    REFLEX = 1
    PERCEPTUAL = 2
    ASSOCIATIVE = 3
    PREDICTIVE = 4
    STRATEGIC = 5
    METACOGNITIVE = 6
    SELF_REPAIRING = 7
    CONSOLIDATED = 8


@dataclass(slots=True)
class DevelopmentScore:
    evidence_volume: float = 0.0
    evidence_quality: float = 0.0
    prediction_accuracy: float = 0.0
    calibration_trend: float = 0.0
    replay_coverage: float = 0.0
    fixture_coverage: float = 0.0
    reward_attribution: float = 0.0
    pain_attribution: float = 0.0
    contradiction_health: float = 0.0
    immune_health: float = 0.0
    operator_independence: float = 0.0
    source_rights_status: float = 0.0
    governance_maturity: float = 0.0
    overfitting_resistance: float = 0.0
    consolidation_status: float = 0.0
    pruning_status: float = 0.0

    @property
    def total(self) -> float:
        values = [_clamp01(getattr(self, item.name)) for item in fields(self)]
        return sum(values) / len(values)


class DevelopmentalStageService:
    """Evidence gate for stage progression; stages cannot be skipped."""

    thresholds = {
        DevelopmentalStage.REFLEX: 0.05,
        DevelopmentalStage.PERCEPTUAL: 0.15,
        DevelopmentalStage.ASSOCIATIVE: 0.28,
        DevelopmentalStage.PREDICTIVE: 0.42,
        DevelopmentalStage.STRATEGIC: 0.56,
        DevelopmentalStage.METACOGNITIVE: 0.68,
        DevelopmentalStage.SELF_REPAIRING: 0.8,
        DevelopmentalStage.CONSOLIDATED: 0.9,
    }

    def eligible_stage(self, score: DevelopmentScore) -> DevelopmentalStage:
        eligible = DevelopmentalStage.REFLEX
        for stage in DevelopmentalStage:
            if score.total >= self.thresholds[stage]:
                eligible = stage
            else:
                break
        return eligible

    def advance(
        self,
        current: DevelopmentalStage,
        requested: DevelopmentalStage,
        score: DevelopmentScore,
        *,
        replay_passed: bool,
        immune_scan_passed: bool,
        rollback_path_exists: bool,
        acceptance_report_exists: bool,
    ) -> DevelopmentalStage:
        if requested <= current:
            return requested
        if int(requested) != int(current) + 1:
            raise ValueError("developmental stages cannot be skipped")
        if self.eligible_stage(score) < requested:
            raise ValueError("development score does not support requested stage")
        if not all(
            [replay_passed, immune_scan_passed, rollback_path_exists, acceptance_report_exists]
        ):
            raise ValueError("developmental promotion requires replay, immune, rollback and acceptance evidence")
        return requested
