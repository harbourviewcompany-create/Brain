from __future__ import annotations

from typing import Any

from .adapters.cognitive_object_store import InMemoryCognitiveObjectStore
from .benchmarks import BenchmarkBaseline, BenchmarkCase, BenchmarkResult, CognitiveBenchmarkLab
from .memory_systems import EpisodicMemory, MultiSystemMemory, SemanticMemory
from .model_cortex import ModelCortexRouter, ModelProfile
from .planning import CounterfactualPlanner, CausalGraph, PlanCandidate
from .world_model import BitemporalWorldModel, WorldObservation


class CognitiveGrowthRuntime:
    """Durable integration spine for world state, memory, models, plans and benchmarks."""

    def __init__(self, store: InMemoryCognitiveObjectStore | None = None) -> None:
        self.store = store or InMemoryCognitiveObjectStore()
        self.world = BitemporalWorldModel()
        self.memory = MultiSystemMemory()
        self.models = ModelCortexRouter()
        self.causal_graph = CausalGraph()
        self.planner = CounterfactualPlanner(self.causal_graph)
        self.benchmarks = CognitiveBenchmarkLab()

    def ingest_world_observation(self, observation: WorldObservation) -> WorldObservation:
        observation = self.world.ingest(observation)
        self.store.save(
            "world_observation",
            observation.id,
            observation,
            source_refs=observation.evidence_refs,
            world_valid_from=observation.world_valid_from,
            world_valid_to=observation.world_valid_to,
        )
        return observation

    def remember_episode(self, episode: EpisodicMemory) -> EpisodicMemory:
        episode = self.memory.remember_episode(episode)
        self.store.save(
            "episodic_memory",
            episode.id,
            episode,
            source_refs=episode.source_refs,
            world_valid_from=episode.occurred_at,
        )
        return episode

    def consolidate_semantic(
        self, statement: str, episode_ids: list, *, confidence: float
    ) -> SemanticMemory:
        semantic = self.memory.consolidate_semantic(statement, episode_ids, confidence=confidence)
        self.store.save(
            "semantic_memory",
            semantic.id,
            semantic,
            source_refs=semantic.source_refs,
        )
        return semantic

    def register_model(self, profile: ModelProfile, *, evidence_refs: list[str]) -> ModelProfile:
        if not evidence_refs:
            raise ValueError("model profile requires performance evidence")
        profile = self.models.register(profile)
        self.store.save("model_profile", profile.id, profile, source_refs=evidence_refs)
        return profile

    def simulate_plan(
        self,
        plan: PlanCandidate,
        baseline: dict[str, float],
    ):
        result = self.planner.simulate(plan, baseline)
        self.store.save(
            "counterfactual_result",
            result.plan_id,
            result,
            source_refs=result.evidence_refs,
        )
        return result

    def evaluate_benchmark(
        self,
        suite_id: str,
        cases: list[BenchmarkCase],
        *,
        commit_sha: str | None = None,
    ) -> tuple[BenchmarkResult, BenchmarkBaseline | None]:
        result = self.benchmarks.evaluate(suite_id, cases)
        self.store.save(
            "benchmark_result",
            result.id,
            result,
            source_refs=result.evidence_refs,
        )
        baseline = None
        if commit_sha:
            baseline = self.benchmarks.baseline(result, commit_sha=commit_sha)
            self.store.save(
                "benchmark_baseline",
                baseline.id,
                baseline,
                source_refs=result.evidence_refs,
            )
        return result, baseline

    def snapshot(self) -> dict[str, Any]:
        return {
            "world_observations": len(self.store.list("world_observation")),
            "episodic_memories": len(self.store.list("episodic_memory")),
            "semantic_memories": len(self.store.list("semantic_memory")),
            "model_profiles": len(self.store.list("model_profile")),
            "counterfactual_results": len(self.store.list("counterfactual_result")),
            "benchmark_results": len(self.store.list("benchmark_result")),
            "benchmark_baselines": len(self.store.list("benchmark_baseline")),
        }
