from __future__ import annotations

from uuid import uuid4

from brain.adapters.developmental_store import InMemoryDevelopmentalStore
from brain.developmental.consolidation import DreamScenario, MemoryRecord
from brain.developmental.global_workspace import WorkspaceItem
from brain.developmental.runtime import DevelopmentalRuntime
from brain.developmental.spine import DevelopmentScore, DevelopmentalStage


def test_learning_signal_persists_development_pressure():
    store = InMemoryDevelopmentalStore()
    runtime = DevelopmentalRuntime(store)
    outcome_id = uuid4()
    pressure = runtime.ingest_learning_signal(
        outcome_id=outcome_id,
        prediction_id=None,
        prediction_error=0.7,
        reward_score=-0.2,
        evidence_refs=[f"outcome:{outcome_id}"],
        evidence_gap=0.8,
    )
    assert pressure.learning_priority > 0.5
    assert len(store.list("prediction_error")) == 1
    assert len(store.list("development_pressure")) == 1


def test_workspace_and_consolidation_are_persisted():
    store = InMemoryDevelopmentalStore()
    runtime = DevelopmentalRuntime(store)
    items = [
        WorkspaceItem(
            "risk",
            "material contradiction",
            ["evidence:risk"],
            salience=1.0,
            intended_consumers=["planner"],
        ),
        WorkspaceItem("noise", "background", ["evidence:noise"], salience=0.1),
    ]
    runtime.run_workspace(items)
    assert len(store.list("workspace_broadcast")) == 1
    assert len(store.list("workspace_suppression")) == 1

    runtime.run_consolidation(
        memories=[MemoryRecord("repeat signal", ["source:1"])],
        scenarios=[DreamScenario("rehearse", ["source:1"], ["propose edge update"])],
    )
    assert len(store.list("consolidation_run")) == 1
    proposal = store.list("dream_rewire_proposal")[0]["payload"]
    assert proposal["external_action_authorized"] is False


def test_immune_scan_quarantines_and_stage_transition_is_audited():
    store = InMemoryDevelopmentalStore()
    runtime = DevelopmentalRuntime(store)
    _, quarantines = runtime.immune_scan(
        target_id="external-action",
        evidence_refs=["audit:missing-approval"],
        approval_required=True,
        approval_present=False,
    )
    assert quarantines
    assert store.list("quarantine")

    score = DevelopmentScore(**{name: 1.0 for name in DevelopmentScore.__dataclass_fields__})
    new_stage = runtime.advance_stage(
        "planner",
        DevelopmentalStage.REFLEX,
        DevelopmentalStage.PERCEPTUAL,
        score,
        evidence_refs=["acceptance:planner"],
        replay_passed=True,
        immune_scan_passed=True,
        rollback_path_exists=True,
        acceptance_report_exists=True,
    )
    assert new_stage is DevelopmentalStage.PERCEPTUAL
    assert store.transitions[0]["module_key"] == "planner"
