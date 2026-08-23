from __future__ import annotations

from datetime import UTC, datetime

from brain.adapters.cognitive_object_store import InMemoryCognitiveObjectStore
from brain.benchmarks import BenchmarkCase
from brain.growth_runtime import CognitiveGrowthRuntime
from brain.memory_systems import EpisodicMemory
from brain.model_cortex import ModelProfile
from brain.world_model import WorldObservation


def test_growth_runtime_persists_world_memory_models_and_benchmarks() -> None:
    store = InMemoryCognitiveObjectStore()
    runtime = CognitiveGrowthRuntime(store)
    observation = runtime.ingest_world_observation(
        WorldObservation(
            "registry",
            "text",
            "Acme active",
            datetime.now(UTC),
            evidence_refs=["registry:1"],
        )
    )
    assert store.get("world_observation", observation.id)

    episode = runtime.remember_episode(
        EpisodicMemory(
            "Acme expanded",
            datetime.now(UTC),
            datetime.now(UTC),
            ["registry:1"],
        )
    )
    semantic = runtime.consolidate_semantic("Acme is expanding", [episode.id], confidence=0.8)
    assert store.get("semantic_memory", semantic.id)

    model = runtime.register_model(
        ModelProfile("provider", "model", {"general": 0.8}, historical_accuracy=0.8),
        evidence_refs=["benchmark:model"],
    )
    assert store.get("model_profile", model.id)

    result, baseline = runtime.evaluate_benchmark(
        "growth",
        [BenchmarkCase("case", "growth", True, True, 0.9, evidence_refs=["eval:1"])],
        commit_sha="abc123",
    )
    assert result.score > 0
    assert baseline is not None
    snapshot = runtime.snapshot()
    assert snapshot["world_observations"] == 1
    assert snapshot["episodic_memories"] == 1
    assert snapshot["semantic_memories"] == 1
    assert snapshot["model_profiles"] == 1
    assert snapshot["benchmark_results"] == 1
    assert snapshot["benchmark_baselines"] == 1
