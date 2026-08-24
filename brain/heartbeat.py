"""Heartbeat: continuous cognition runner + closed sensory→learning loop.

Composes:
  sensory inbox → CognitiveCycle (perceive / attend / evidence / belief) →
  optional prediction → outcome attribution (via LearningService)

The heartbeat is the process that makes the Brain keep thinking between
operator HTTP calls. Production deployments should run `run_forever` in a
worker process (or call `tick` on a schedule).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

from .cycle import CognitiveCycle, CognitiveCycleResult
from .domain import Outcome
from .events import BrainEvent
from .learning import LearningService
from .memory import InMemoryBrainStore
from .prediction import Prediction
from .runner import ContinuousCognitionRunner
from .sensory_inbox import InMemorySensoryInbox, InboxItem


@dataclass(slots=True)
class CycleRunRecord:
    inbox_id: UUID
    result: CognitiveCycleResult


@dataclass
class HeartbeatService:
    """Operator-facing façade over inbox + cycle runner + learning loop."""

    event_store: Any
    learning: LearningService | None = None
    inbox: InMemorySensoryInbox = field(default_factory=InMemorySensoryInbox)
    attention_threshold: float = 0.0
    cognitive_budget: int = 2
    auto_predict: bool = True
    idle_sleep_seconds: float = 1.0

    def __post_init__(self) -> None:
        self._cycle = CognitiveCycle(
            self.event_store,
            attention_threshold=self.attention_threshold,
            cognitive_budget=self.cognitive_budget,
        )
        self._runs: list[CycleRunRecord] = []
        self._runs_lock = Lock()
        self._ticks: int = 0
        self._processed: int = 0

        class _RunsAdapter:
            def __init__(self, outer: HeartbeatService) -> None:
                self._outer = outer

            def save(self, inbox_id: UUID, result: CognitiveCycleResult) -> None:
                with self._outer._runs_lock:
                    self._outer._runs.append(CycleRunRecord(inbox_id, result))

        self._runner = ContinuousCognitionRunner(
            cycle=self._cycle,
            inbox=self.inbox,
            cycle_runs=_RunsAdapter(self),
            idle_sleep_seconds=self.idle_sleep_seconds,
        )

    def perceive(
        self,
        *,
        content: str,
        claim: str,
        source_key: str = "operator",
        source_reliability: float = 0.7,
        supports: bool = True,
        belief_statement: str | None = None,
        belief_confidence: float = 0.5,
        novelty: float = 0.5,
        urgency: float = 0.3,
        commercial_upside: float = 0.0,
        contradiction_value: float = 0.0,
        uncertainty_reduction: float = 0.5,
        noise_probability: float = 0.2,
        operator_burden: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> InboxItem:
        """Enqueue a sensory stimulus for the next tick."""
        payload = {
            "source_reliability": source_reliability,
            "supports": supports,
            "belief_statement": belief_statement or claim,
            "belief_confidence": belief_confidence,
            "novelty": novelty,
            "urgency": urgency,
            "commercial_upside": commercial_upside,
            "contradiction_value": contradiction_value,
            "uncertainty_reduction": uncertainty_reduction,
            "noise_probability": noise_probability,
            "operator_burden": operator_burden,
            "metadata": dict(metadata or {}),
        }
        item = self.inbox.enqueue(
            source_key=source_key,
            content=content,
            claim=claim,
            payload=payload,
        )
        if hasattr(self.event_store, "append"):
            self.event_store.append(
                BrainEvent(
                    "signal.enqueued",
                    "sensory_inbox",
                    item.id,
                    {
                        "source_key": source_key,
                        "content": content,
                        "claim": claim,
                        "payload": payload,
                    },
                )
            )
        return item

    def tick(self, *, max_items: int = 1) -> dict[str, Any]:
        """Run up to max_items cognition cycles. Returns a status snapshot."""
        processed: list[dict[str, Any]] = []
        for _ in range(max(1, max_items)):
            before = len(self._runs)
            worked = self._runner.run_once()
            self._ticks += 1
            if not worked:
                break
            self._processed += 1
            with self._runs_lock:
                if len(self._runs) > before:
                    rec = self._runs[-1]
                    processed.append(
                        {
                            "inbox_id": str(rec.inbox_id),
                            "cycle_id": str(rec.result.cycle_id),
                            "belief_id": str(rec.result.belief_id),
                            "evidence_id": str(rec.result.evidence_id),
                            "attention_score": rec.result.attention_score,
                            "contradiction_detected": rec.result.contradiction_detected,
                            "working_memory_size": rec.result.working_memory_size,
                        }
                    )
                    if self.auto_predict and self.learning is not None:
                        pred = self._maybe_predict(rec.result)
                        if pred is not None:
                            processed[-1]["prediction_id"] = str(pred.id)
        return {
            "ticks": self._ticks,
            "processed_this_call": len(processed),
            "total_processed": self._processed,
            "cycles": processed,
            "inbox": self.inbox.stats(),
        }

    def run_forever(self) -> None:
        """Blocking worker loop — use in a dedicated process/container."""
        self._runner.run_forever()

    def _maybe_predict(self, result: CognitiveCycleResult) -> Prediction | None:
        """Create an open prediction from a high-attention belief update."""
        if self.learning is None:
            return None
        if result.attention_score < 0.3:
            return None
        belief = self._cycle._belief_cache.get(result.belief_id)
        statement = belief.statement if belief is not None else "belief outcome"
        confidence = belief.confidence if belief is not None else 0.5
        pred = Prediction(
            statement=f"Observation will support: {statement}",
            expected_value=1.0 if confidence >= 0.5 else 0.0,
            confidence=min(0.95, max(0.05, confidence)),
            horizon=timedelta(hours=24),
            belief_id=result.belief_id,
            metadata={"cycle_id": str(result.cycle_id), "auto": True},
        )
        return self.learning.create_prediction(pred)

    def resolve_with_outcome(
        self,
        *,
        prediction_id: UUID,
        value_created: float,
        action_id: UUID | None = None,
        prediction_accuracy: float = 0.5,
        operator_time_cost: float = 0.0,
        source_keys: list[str] | None = None,
        edge_ids: list[UUID] | None = None,
    ) -> Any:
        """Close the loop: outcome → attribution → rewire via LearningService."""
        if self.learning is None:
            raise RuntimeError("learning_service_unavailable")
        outcome = Outcome(
            action_id=action_id or uuid4(),
            value_created=value_created,
            operator_time_cost=operator_time_cost,
            prediction_accuracy=prediction_accuracy,
            prediction_id=prediction_id,
            edge_ids=list(edge_ids or []),
            source_keys=list(source_keys or []),
        )
        return self.learning.record_outcome(
            outcome,
            prediction_id=prediction_id,
            edge_ids=edge_ids,
            source_keys=source_keys,
        )

    def status(self) -> dict[str, Any]:
        with self._runs_lock:
            last = None
            if self._runs:
                r = self._runs[-1]
                last = {
                    "inbox_id": str(r.inbox_id),
                    "cycle_id": str(r.result.cycle_id),
                    "belief_id": str(r.result.belief_id),
                    "attention_score": r.result.attention_score,
                }
        return {
            "ticks": self._ticks,
            "total_processed": self._processed,
            "inbox": self.inbox.stats(),
            "belief_cache_size": len(self._cycle._belief_cache),
            "working_memory_size": self._cycle.working_memory.size,
            "last_cycle": last,
            "auto_predict": self.auto_predict,
        }


def build_default_heartbeat(
    *,
    event_store: Any | None = None,
    learning: LearningService | None = None,
) -> HeartbeatService:
    store = event_store or InMemoryBrainStore()
    return HeartbeatService(event_store=store, learning=learning)
