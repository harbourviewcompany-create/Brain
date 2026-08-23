from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from brain.benchmarks import BenchmarkCase, CognitiveBenchmarkLab
from brain.developmental.sandbox import CandidateModuleBuild, SandboxReplay, SelfModificationSandbox
from brain.memory_systems import EpisodicMemory, MultiSystemMemory, ProceduralMemory, ProspectiveMemory
from brain.world_model import BitemporalWorldModel, WorldObservation


def test_benchmark_lab_detects_regression_against_exact_commit_baseline() -> None:
    lab = CognitiveBenchmarkLab()
    good_cases = [
        BenchmarkCase("a", "prediction", True, True, 0.9, latency_ms=100, cost=0.1, evidence_refs=["eval:a"]),
        BenchmarkCase("b", "prediction", False, False, 0.1, latency_ms=120, cost=0.1, evidence_refs=["eval:b"]),
    ]
    baseline_result = lab.evaluate("prediction-suite", good_cases)
    baseline = lab.baseline(baseline_result, commit_sha="abc123")
    weak_cases = [
        BenchmarkCase("a", "prediction", True, False, 0.2, latency_ms=3000, cost=5, evidence_refs=["eval:a2"]),
        BenchmarkCase("b", "prediction", False, True, 0.8, latency_ms=3000, cost=5, evidence_refs=["eval:b2"]),
    ]
    candidate = lab.evaluate("prediction-suite", weak_cases)
    decision = lab.compare(candidate, baseline)
    assert decision.passed is False
    assert decision.regressions


def test_world_model_preserves_world_time_learning_time_and_change_provenance() -> None:
    model = BitemporalWorldModel()
    world_time = datetime(2026, 8, 1, tzinfo=UTC)
    first = model.ingest(
        WorldObservation(
            "registry",
            "text",
            "Acme status active",
            world_time,
            evidence_refs=["registry:1"],
        )
    )
    entity = model.resolve_entity(
        name="Acme",
        kind="company",
        observation_id=first.id,
        attributes={"status": "active"},
    )
    second = model.ingest(
        WorldObservation(
            "registry",
            "text",
            "Acme status dissolved",
            world_time + timedelta(days=10),
            evidence_refs=["registry:2"],
        )
    )
    model.resolve_entity(
        name="Acme",
        kind="company",
        observation_id=second.id,
        attributes={"status": "dissolved"},
    )
    assert model.changes[0].world_valid_at == world_time + timedelta(days=10)
    assert model.changes[0].learned_at == second.observed_at
    assert model.state_as_of(entity.id, world_time + timedelta(days=5))["status"] == "active"


def test_multi_system_memory_prevents_source_amnesia_and_supports_reconsolidation() -> None:
    memory = MultiSystemMemory()
    episode = memory.remember_episode(
        EpisodicMemory(
            "buyer requested faster delivery",
            datetime.now(UTC),
            datetime.now(UTC),
            ["call:1"],
            salience=0.9,
            confidence=0.8,
        )
    )
    semantic = memory.consolidate_semantic(
        "buyer values delivery speed",
        [episode.id],
        confidence=0.8,
    )
    assert semantic.source_refs == ["call:1"]
    retrieval = memory.retrieve_episodes("buyer delivery")
    assert retrieval[0].source_refs == ["call:1"]
    revised, record = memory.reconsolidate_episode(
        episode.id,
        revised_content="buyer requested faster delivery for urgent orders",
        reason="new context",
        evidence_refs=["email:2"],
    )
    assert set(revised.source_refs) == {"call:1", "email:2"}
    assert memory.rollback_reconsolidation(record).content == "buyer requested faster delivery"


def test_procedural_and_prospective_memory_are_outcome_and_trigger_aware() -> None:
    memory = MultiSystemMemory()
    procedure = memory.remember_procedure(
        ProceduralMemory("verify buyer", ["check registry", "confirm authority"], ["playbook:1"])
    )
    memory.record_procedure_outcome(procedure.id, success=True)
    assert procedure.success_count == 1
    intention = memory.remember_intention(
        ProspectiveMemory("recheck permit", None, "permit_changed", ["source:permit"])
    )
    assert memory.due_intentions(trigger="permit_changed") == [intention]


def test_self_modification_sandbox_blocks_regression_and_external_action() -> None:
    lab = CognitiveBenchmarkLab()
    baseline_result = lab.evaluate(
        "module-suite",
        [BenchmarkCase("a", "module", True, True, 0.9, evidence_refs=["eval:base"])],
    )
    baseline = lab.baseline(baseline_result, commit_sha="base-sha")
    candidate_result = lab.evaluate(
        "module-suite",
        [BenchmarkCase("a", "module", True, False, 0.2, evidence_refs=["eval:candidate"])],
    )
    candidate = CandidateModuleBuild(
        "new module",
        ["source:1"],
        ["schema:1"],
        ["service:1"],
        ["fixture:1"],
        ["test:1"],
        ["acceptance:1"],
        ["rollback:1"],
    )
    replay = SandboxReplay(candidate.id, "replay-1", True, 0, ["replay:evidence"])
    proposal, decision = SelfModificationSandbox().evaluate(
        candidate,
        replay=replay,
        candidate_benchmark=candidate_result,
        baseline=baseline,
        immune_scan_passed=True,
    )
    assert decision.passed is False
    assert proposal.promotion_allowed is False
    assert proposal.external_action_authorized is False


def test_self_modification_candidate_requires_complete_artifacts() -> None:
    candidate = CandidateModuleBuild("bad", [], [], [], [], [], [], [])
    with pytest.raises(ValueError, match="candidate module missing"):
        SelfModificationSandbox.validate_candidate(candidate)
