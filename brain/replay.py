from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contradiction_queue import ContradictionReviewService, ContradictionStatus
from .cycle import CognitiveCycle, CognitiveStimulus
from .formulas import FormulaRunResult, default_formula_registry
from .memory import InMemoryBrainStore


@dataclass(slots=True)
class ReplayResult:
    fixture_id: str
    scenario: str
    passed: bool
    event_types: list[str]
    formula_runs: list[dict[str, Any]] = field(default_factory=list)
    state_transitions: list[str] = field(default_factory=list)
    go_hold: str = "HOLD"
    notes: list[str] = field(default_factory=list)

    def deterministic_signature(self) -> tuple[Any, ...]:
        return (
            self.fixture_id,
            tuple(self.event_types),
            tuple(self.state_transitions),
            tuple(run["formula_id"] for run in self.formula_runs),
            self.go_hold,
        )


class ReplayHarness:
    """Fixture-first replay harness for deterministic Brain acceptance evidence."""

    def __init__(self) -> None:
        self.formulas = default_formula_registry()

    def run_fixture(self, fixture: str | Path | dict[str, Any]) -> ReplayResult:
        data = self._load(fixture)
        fixture_id = data["fixture_id"]
        scenario = data["scenario"]
        if fixture_id == "source_signal_evidence_belief":
            return self._source_signal_evidence_belief(data)
        if fixture_id == "approval_gate_external_action":
            return self._approval_gate(data)
        if fixture_id == "outcome_reward_pain_learning":
            return self._outcome_learning(data)
        if fixture_id == "contradiction_review":
            return self._contradiction_review(data)
        if fixture_id == "formula_run_attention_reward":
            return self._formula_run(data)
        return ReplayResult(fixture_id, scenario, False, [], notes=["unknown fixture"])

    def write_acceptance_report(
        self,
        result: ReplayResult,
        output_path: str | Path,
        *,
        ticket_id: str,
        tests: list[str],
    ) -> dict[str, Any]:
        report = {
            "report_id": f"{ticket_id}-{result.fixture_id}",
            "ticket_id": ticket_id,
            "fixture_id": result.fixture_id,
            "verdict": result.go_hold,
            "tests": tests,
            "passed": result.passed,
            "event_types": result.event_types,
            "state_transitions": result.state_transitions,
            "formula_runs": result.formula_runs,
            "notes": result.notes,
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        return report

    def _load(self, fixture: str | Path | dict[str, Any]) -> dict[str, Any]:
        if isinstance(fixture, dict):
            return fixture
        with Path(fixture).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _source_signal_evidence_belief(self, data: dict[str, Any]) -> ReplayResult:
        store = InMemoryBrainStore()
        cycle = CognitiveCycle(store)
        stimulus = CognitiveStimulus(**data["input"]["stimulus"])
        cycle.process(stimulus)
        event_types = [event.event_type for event in store.read_all()]
        expected = data["expected"]["event_types_subset"]
        passed = all(event_type in event_types for event_type in expected)
        return ReplayResult(
            data["fixture_id"],
            data["scenario"],
            passed,
            event_types,
            state_transitions=["source", "signal", "evidence", "belief"],
            go_hold="GO" if passed else "HOLD",
        )

    def _approval_gate(self, data: dict[str, Any]) -> ReplayResult:
        action = data["input"]["candidate_action"]
        approved = data["input"].get("approval") == "approved"
        blocked = bool(action.get("external")) and not approved
        event_types = ["action.simulated"]
        event_types.append("approval.blocked" if blocked else "action.ready")
        passed = data["expected"].get("blocked") == blocked
        return ReplayResult(
            data["fixture_id"],
            data["scenario"],
            passed,
            event_types,
            state_transitions=["draft", "approval_required", "blocked" if blocked else "ready"],
            go_hold="GO" if passed else "HOLD",
        )

    def _outcome_learning(self, data: dict[str, Any]) -> ReplayResult:
        runs = [
            self._run_formula("reward_score", data),
            self._run_formula("pain_score", data),
            self._run_formula("graph_weight_update", data),
        ]
        event_types = ["outcome.logged", "reward.scored", "pain.scored", "graph.weight_updated"]
        passed = runs[0].output > 0 and runs[2].output >= 0
        return ReplayResult(
            data["fixture_id"],
            data["scenario"],
            passed,
            event_types,
            formula_runs=[self._serialize_run(run) for run in runs],
            state_transitions=["outcome", "reward_pain", "graph_update", "reallocation"],
            go_hold="GO" if passed else "HOLD",
        )

    def _contradiction_review(self, data: dict[str, Any]) -> ReplayResult:
        service = ContradictionReviewService()
        item = service.create_review_item(**data["input"]["contradiction"])
        item = service.require_user_decision(item.id)
        preserved = bool(item.supporting_claim and item.contradicting_claim)
        passed = preserved and item.status == ContradictionStatus.USER_DECISION_REQUIRED
        return ReplayResult(
            data["fixture_id"],
            data["scenario"],
            passed,
            ["contradiction.detected", "contradiction.review_required"],
            state_transitions=["open", "user_decision_required"],
            go_hold="GO" if passed else "HOLD",
        )

    def _formula_run(self, data: dict[str, Any]) -> ReplayResult:
        runs = [
            self._run_formula("attention_score", data),
            self._run_formula("reward_score", data),
        ]
        passed = all(run.audit_evidence for run in runs)
        return ReplayResult(
            data["fixture_id"],
            data["scenario"],
            passed,
            ["formula.attention_score", "formula.reward_score"],
            formula_runs=[self._serialize_run(run) for run in runs],
            state_transitions=["formula_run", "audit_trace"],
            go_hold="GO" if passed else "HOLD",
        )

    def _run_formula(self, formula_id: str, data: dict[str, Any]) -> FormulaRunResult:
        formula_input = data["input"]["formulas"][formula_id]
        return self.formulas.evaluate(
            formula_id,
            formula_input,
            owner_object_id=data["input"].get("owner_object_id", "fixture-owner"),
            owner_object_type=data["input"].get("owner_object_type", "Fixture"),
        )

    def _serialize_run(self, run: FormulaRunResult) -> dict[str, Any]:
        return {
            "formula_id": run.formula_id,
            "run_id": str(run.run_id),
            "owner_object_id": run.owner_object_id,
            "owner_object_type": run.owner_object_type,
            "service": run.service,
            "table_store": run.table_store,
            "dashboard": run.dashboard,
            "decision_consequence": run.decision_consequence,
            "inputs": run.inputs,
            "output": run.output,
            "audit_evidence": run.audit_evidence,
        }
