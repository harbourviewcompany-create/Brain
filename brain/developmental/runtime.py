from __future__ import annotations

from dataclasses import fields
from uuid import UUID

from ..adapters.developmental_store import InMemoryDevelopmentalStore
from .consolidation import ConsolidationService, DreamScenario, MemoryRecord
from .global_workspace import BroadcastService, WorkspaceCompetitionService, WorkspaceItem
from .immune import CognitiveImmuneService, QuarantineService
from .prediction_error import DevelopmentPressure, DevelopmentPressureService, PredictionError
from .spine import DevelopmentScore, DevelopmentalStage, DevelopmentalStageService


class DevelopmentalRuntime:
    """Persistent integration surface for controlled cognitive development."""

    def __init__(self, store: InMemoryDevelopmentalStore | None = None) -> None:
        self.store = store or InMemoryDevelopmentalStore()
        self.pressure = DevelopmentPressureService()
        self.workspace = WorkspaceCompetitionService()
        self.broadcasts = BroadcastService()
        self.consolidation = ConsolidationService()
        self.immune = CognitiveImmuneService()
        self.quarantine = QuarantineService()
        self.stages = DevelopmentalStageService()

    def ingest_learning_signal(
        self,
        *,
        outcome_id: UUID,
        prediction_id: UUID | None,
        prediction_error: float,
        reward_score: float,
        evidence_refs: list[str],
        contradiction_burden: float = 0.0,
        evidence_gap: float = 0.0,
    ) -> DevelopmentPressure:
        if not evidence_refs:
            raise ValueError("developmental learning requires attribution evidence")
        effective_prediction_id = prediction_id or outcome_id
        error = PredictionError(
            prediction_id=effective_prediction_id,
            actual_value=reward_score,
            signed_error=reward_score,
            absolute_error=abs(float(prediction_error)),
            surprise=max(0.0, min(1.0, abs(float(prediction_error)))),
        )
        pressure = self.pressure.score(
            error,
            contradiction_burden=contradiction_burden,
            evidence_gap=evidence_gap,
        )
        self.store.save("prediction_error", error.id, error, evidence_refs)
        self.store.save("development_pressure", pressure.id, pressure, evidence_refs)
        return pressure

    def run_workspace(
        self,
        items: list[WorkspaceItem],
        *,
        capacity: int = 1,
        consumers: list[str] | None = None,
    ):
        coalition, suppressions = self.workspace.compete(items, capacity=capacity)
        broadcast = self.broadcasts.broadcast(coalition, items, consumers=consumers)
        evidence = list(broadcast.evidence_refs)
        self.store.save("workspace_coalition", coalition.id, coalition, evidence)
        for event in suppressions:
            item = next((item for item in items if item.id == event.item_id), None)
            self.store.save(
                "workspace_suppression",
                event.id,
                event,
                list(item.evidence_refs) if item else evidence,
            )
        self.store.save("workspace_broadcast", broadcast.id, broadcast, evidence)
        return coalition, suppressions, broadcast

    def run_consolidation(self, *, memories: list[MemoryRecord], scenarios: list[DreamScenario]):
        run, compressions, rehearsals, proposals = self.consolidation.run(
            memories=memories,
            scenarios=scenarios,
        )
        self.store.save("consolidation_run", run.id, run, run.source_refs)
        for compression in compressions:
            self.store.save("memory_compression", compression.id, compression, compression.source_refs)
        for rehearsal in rehearsals:
            self.store.save("rehearsal_trace", rehearsal.id, rehearsal, rehearsal.source_refs)
        for proposal in proposals:
            self.store.save("dream_rewire_proposal", proposal.id, proposal, proposal.source_refs)
        return run, compressions, rehearsals, proposals

    def immune_scan(self, *, target_id: str, evidence_refs: list[str], **signals):
        alerts = self.immune.scan(target_id=target_id, evidence_refs=evidence_refs, **signals)
        quarantines = []
        for alert in alerts:
            self.store.save("immune_alert", alert.id, alert, alert.evidence_refs)
            if alert.severity.value in {"high", "critical"}:
                record = self.quarantine.quarantine(target_id, alert)
                quarantines.append(record)
                self.store.save("quarantine", record.id, record, alert.evidence_refs)
        return alerts, quarantines

    def record_development_score(self, module_key: str, score: DevelopmentScore) -> float:
        dimensions = {item.name: float(getattr(score, item.name)) for item in fields(score)}
        self.store.save_score(module_key, score.total, dimensions)
        return score.total

    def advance_stage(
        self,
        module_key: str,
        current: DevelopmentalStage,
        requested: DevelopmentalStage,
        score: DevelopmentScore,
        *,
        evidence_refs: list[str],
        replay_passed: bool,
        immune_scan_passed: bool,
        rollback_path_exists: bool,
        acceptance_report_exists: bool,
    ) -> DevelopmentalStage:
        if not evidence_refs:
            raise ValueError("developmental transition requires evidence")
        new_stage = self.stages.advance(
            current,
            requested,
            score,
            replay_passed=replay_passed,
            immune_scan_passed=immune_scan_passed,
            rollback_path_exists=rollback_path_exists,
            acceptance_report_exists=acceptance_report_exists,
        )
        self.store.log_transition(
            module_key,
            current.name.lower(),
            new_stage.name.lower(),
            evidence_refs,
            "developmental_stage_promotion",
        )
        return new_stage
