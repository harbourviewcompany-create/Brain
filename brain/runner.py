"""Continuous cognition runner — inbox cycles + endogenous mind."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Callable
from uuid import uuid4
from .cycle import CognitiveCycle, CognitiveStimulus
from .domain import Outcome
from .endogenous import ENDOGENOUS_SOURCE_KEY, EndogenousStimulus
from .mind_runtime import MindRuntime
from .prediction import Prediction

@dataclass(slots=True)
class ContinuousCognitionRunner:
    cycle: CognitiveCycle
    inbox: Any
    cycle_runs: Any
    idle_sleep_seconds: float = 1.0
    max_attempts: int = 5
    enable_endogenous: bool = True
    mind: MindRuntime = field(default_factory=MindRuntime)
    status_provider: Callable[[], dict[str, Any]] | None = None
    learning: Any | None = None
    auto_predict: bool = True
    night_check_every: int = 3
    _idle_cycles: int = 0

    def run_once(self) -> bool:
        item = self.inbox.claim_next()
        if item is None:
            if not self.enable_endogenous:
                return False
            return self._run_endogenous()
        return self._process_inbox_item(item)

    def _process_inbox_item(self, item: dict[str, Any]) -> bool:
        try:
            payload = dict(item.get("payload") or {})
            result = self.cycle.process(CognitiveStimulus(
                content=item["content"], source_id=item["source_key"], claim=item["claim"],
                source_reliability=float(payload.get("source_reliability", 0.5)),
                supports=bool(payload.get("supports", True)),
                belief_statement=payload.get("belief_statement"),
                belief_confidence=float(payload.get("belief_confidence", 0.5)),
                commercial_upside=float(payload.get("commercial_upside", 0.0)),
                novelty=float(payload.get("novelty", 0.5)), urgency=float(payload.get("urgency", 0.0)),
                contradiction_value=float(payload.get("contradiction_value", 0.0)),
                uncertainty_reduction=float(payload.get("uncertainty_reduction", 0.5)),
                noise_probability=float(payload.get("noise_probability", 0.2)),
                operator_burden=float(payload.get("operator_burden", 0.0)),
                metadata=payload.get("metadata", {}) or {},
            ))
            self.cycle_runs.save(item["id"], result)
            self.inbox.complete(item["id"])
            self._after_cycle(result, claim=item["claim"], content=item["content"], source_key=item["source_key"])
            return True
        except Exception as exc:
            attempts = int(item.get("attempts") or 0)
            if attempts + 1 >= self.max_attempts:
                self.inbox.fail(item["id"], str(exc), retry=False)
            else:
                self.inbox.fail(item["id"], str(exc), retry=True)
            return True

    def _run_endogenous(self) -> bool:
        self._idle_cycles += 1
        beliefs = list(getattr(self.cycle, "_belief_cache", {}).values())
        status = self.status_provider() if self.status_provider else {}
        phase = getattr(getattr(self.cycle, "circadian", None), "phase", None)
        wm_items = self._wm_items()
        if self._idle_cycles % max(1, self.night_check_every) == 0:
            self._maybe_night_phase(beliefs)
        thought = self.mind.next_endogenous_stimulus(
            beliefs=beliefs, working_memory_items=wm_items or None, self_status=status, circadian_phase=phase)
        if thought is None:
            return False
        inbox_id = self._enqueue_thought(thought)
        try:
            result = self.cycle.process(CognitiveStimulus(
                content=thought.content, source_id=thought.source_key, claim=thought.claim,
                source_reliability=thought.source_reliability, supports=True,
                belief_statement=thought.claim, belief_confidence=0.45, commercial_upside=0.0,
                novelty=thought.novelty, urgency=thought.urgency,
                contradiction_value=thought.contradiction_value,
                uncertainty_reduction=thought.uncertainty_reduction, noise_probability=0.05,
                operator_burden=0.0, metadata=thought.as_inbox_payload().get("metadata") or {},
            ))
            if hasattr(self.cycle_runs, "save") and inbox_id is not None:
                try: self.cycle_runs.save(inbox_id, result)
                except Exception: pass
            if inbox_id is not None and hasattr(self.inbox, "complete"):
                try: self.inbox.complete(inbox_id)
                except Exception: pass
            self._after_cycle(result, claim=thought.claim, content=thought.content, source_key=thought.source_key)
            return True
        except Exception:
            if inbox_id is not None and hasattr(self.inbox, "fail"):
                try: self.inbox.fail(inbox_id, "endogenous_cycle_failed", retry=False)
                except Exception: pass
            return False

    def _after_cycle(self, result: Any, *, claim: str, content: str, source_key: str) -> None:
        beliefs = list(getattr(self.cycle, "_belief_cache", {}).values())
        self.mind.try_auto_resolve_from_claim(claim, content)
        try:
            self.mind.broadcast_focus(title=claim[:120], content=content[:500],
                salience=0.55, novelty=0.5, urgency=0.3, source_refs=[source_key or ENDOGENOUS_SOURCE_KEY])
        except Exception: pass
        if self.auto_predict and self.learning is not None:
            self._emit_prediction(claim=claim, result=result, source_key=source_key)
        try:
            self.mind.refresh_policy(belief_count=len(beliefs), open_curiosity=self.mind.curiosity_open_count(),
                overload_hint=float((self.status_provider() or {}).get("resource_pressure") or 0.0))
        except Exception: pass

    def _emit_prediction(self, *, claim: str, result: Any, source_key: str) -> None:
        if self.learning is None or not hasattr(self.learning, "emit_prediction"):
            return
        statement = (claim or "").strip() or "next observation supports current focus"
        try:
            pred = Prediction(
                statement=f"Endogenous forecast: observation will support [{statement}]",
                expected_value=0.55, confidence=0.45, horizon=timedelta(hours=24),
                domain=str(getattr(result, "domain", None) or "general"),
                source_keys=[ENDOGENOUS_SOURCE_KEY],
                metadata={"endogenous": True, "claim": statement[:200], "cycle_id": str(getattr(result, "id", ""))},
            )
            self.learning.emit_prediction(pred)
        except Exception: pass

    def inject_outcome(self, *, value_created: float = 0.5, prediction_accuracy: float = 0.5,
                       operator_time_cost: float = 0.0, source_keys: list[str] | None = None) -> Any:
        if self.learning is None or not hasattr(self.learning, "inject_outcome"):
            return None
        outcome = Outcome(value_created=value_created, prediction_accuracy=prediction_accuracy,
            operator_time_cost=operator_time_cost, source_keys=list(source_keys or [ENDOGENOUS_SOURCE_KEY]))
        try:
            result = self.learning.inject_outcome(outcome)
            self.mind.buffer_outcome(outcome)
            return result
        except Exception:
            return None

    def _maybe_night_phase(self, beliefs: list[Any]) -> None:
        phase = getattr(getattr(self.cycle, "circadian", None), "phase", None)
        if phase is None: return
        try:
            self.mind.run_night_phase(circadian_phase=phase, beliefs=beliefs,
                event_store=getattr(self.cycle, "event_store", None) or getattr(self, "event_store", None))
        except Exception: pass

    def _wm_items(self) -> list[Any]:
        wm = getattr(self.cycle, "working_memory", None)
        if wm is None: return []
        if hasattr(wm, "items"): return list(wm.items)[:12]
        if hasattr(wm, "snapshot"):
            try:
                snap = wm.snapshot()
                if isinstance(snap, dict): return list(snap.get("items") or [])[:12]
                return list(snap)[:12] if snap else []
            except Exception: return []
        return []

    def _enqueue_thought(self, thought: EndogenousStimulus) -> Any:
        if not hasattr(self.inbox, "enqueue"): return None
        try:
            payload = thought.as_inbox_payload()
            return self.inbox.enqueue(source_key=thought.source_key, content=thought.content,
                claim=thought.claim, payload=payload)
        except Exception: return None

    def run_forever(self) -> None:
        while True:
            if not self.run_once():
                time.sleep(self.idle_sleep_seconds)
