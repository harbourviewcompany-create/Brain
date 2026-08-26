"""Heartbeat service — tick cycles, bootstrap mind, status, outcome inject."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from .cycle import CognitiveCycle, CognitiveCycleResult, CognitiveStimulus
from .domain import Outcome
from .endogenous import seed_foundational_beliefs
from .learning import LearningService
from .memory import InMemoryBrainStore
from .mind_runtime import MindRuntime
from .prediction import Prediction
from .runner import ContinuousCognitionRunner
from .sensory_inbox import InMemorySensoryInbox

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(slots=True)
class CycleRunRecord:
    inbox_id: str
    result: CognitiveCycleResult
    saved_at: datetime = field(default_factory=_utcnow)

class _InMemoryCycleRuns:
    def __init__(self) -> None:
        self._items: dict[str, CycleRunRecord] = {}
    def save(self, inbox_id: str, result: CognitiveCycleResult) -> None:
        self._items[str(inbox_id)] = CycleRunRecord(inbox_id=str(inbox_id), result=result)
    def get(self, inbox_id: str) -> CycleRunRecord | None:
        return self._items.get(str(inbox_id))

@dataclass
class HeartbeatService:
    event_store: Any = field(default_factory=InMemoryBrainStore)
    inbox: Any = field(default_factory=InMemorySensoryInbox)
    learning: LearningService | None = None
    cycle: CognitiveCycle | None = None
    runner: ContinuousCognitionRunner | None = None
    cycle_runs: Any = field(default_factory=_InMemoryCycleRuns)
    mind_runtime: MindRuntime = field(default_factory=MindRuntime)
    _bootstrapped: bool = False

    def __post_init__(self) -> None:
        if self.cycle is None:
            from .cycle import CognitiveCycle
            self.cycle = CognitiveCycle(event_store=self.event_store)
        if self.runner is None:
            self.runner = ContinuousCognitionRunner(
                cycle=self.cycle, inbox=self.inbox, cycle_runs=self.cycle_runs,
                enable_endogenous=True, mind=self.mind_runtime, learning=self.learning,
                status_provider=lambda: self.status(),
            )
        else:
            self.runner.mind = self.mind_runtime
            self.runner.enable_endogenous = True
            if self.learning is not None:
                self.runner.learning = self.learning

    def perceive(self, *, source_key: str, content: str, claim: str,
                 payload: dict[str, Any] | None = None) -> Any:
        return self.inbox.enqueue(source_key=source_key, content=content, claim=claim, payload=payload or {})

    def bootstrap_mind(self) -> int:
        if self._bootstrapped:
            return 0
        seeds = seed_foundational_beliefs()
        cache = getattr(self.cycle, "_belief_cache", None)
        if cache is None:
            self.cycle._belief_cache = {}
            cache = self.cycle._belief_cache
        added = 0
        for b in seeds:
            key = str(getattr(b, "id", None) or getattr(b, "statement", "")[:80])
            if key not in cache:
                cache[key] = b
                added += 1
        self._bootstrapped = True
        return added

    def tick(self, *, max_items: int = 1) -> dict[str, Any]:
        if not self._bootstrapped:
            self.bootstrap_mind()
        processed = 0
        for _ in range(max(1, max_items)):
            if self.runner and self.runner.run_once():
                processed += 1
            else:
                break
        return {
            "processed_this_call": processed,
            "total_processed": processed,
            "pending": (self.inbox.stats() or {}).get("pending", 0) if hasattr(self.inbox, "stats") else 0,
        }

    def run_forever(self) -> None:
        if not self._bootstrapped:
            self.bootstrap_mind()
        if self.runner:
            self.runner.run_forever()

    def mind(self) -> MindRuntime:
        return self.mind_runtime

    def status(self) -> dict[str, Any]:
        inbox_stats = self.inbox.stats() if hasattr(self.inbox, "stats") else {}
        belief_n = len(getattr(self.cycle, "_belief_cache", {}) or {})
        mind_st = self.mind_runtime.status() if hasattr(self.mind_runtime, "status") else {}
        return {
            "inbox": inbox_stats,
            "belief_cache_size": belief_n,
            "bootstrapped": self._bootstrapped,
            "mind": mind_st,
            "resource_pressure": float(mind_st.get("policy", {}).get("overload", 0) or 0) if isinstance(mind_st.get("policy"), dict) else 0.0,
        }

    def inject_outcome(self, *, value_created: float = 0.5, prediction_accuracy: float = 0.5,
                       operator_time_cost: float = 0.0) -> Any:
        if self.runner is not None and hasattr(self.runner, "inject_outcome"):
            return self.runner.inject_outcome(
                value_created=value_created, prediction_accuracy=prediction_accuracy,
                operator_time_cost=operator_time_cost)
        return None

    def resolve_with_outcome(self, *, value_created: float = 0.5, prediction_accuracy: float = 0.5) -> Any:
        return self.inject_outcome(value_created=value_created, prediction_accuracy=prediction_accuracy)

def build_default_heartbeat(*, event_store: Any | None = None, learning: LearningService | None = None,
                            with_learning: bool = True) -> HeartbeatService:
    store = event_store or InMemoryBrainStore()
    if learning is None and with_learning:
        try:
            from brain.adapters.learning_store import InMemoryLearningStore
            from brain.learning import LearningService as LS
            mem = InMemoryLearningStore()
            learning = LS(store, predictions=mem, edges=mem, attributions=mem, sources=mem)
        except Exception:
            learning = None
    return HeartbeatService(event_store=store, learning=learning)
