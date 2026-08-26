"""Mind runtime — endogenous loop orchestration, GWT, policy, night phase."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4
from .curiosity import CuriosityEngine
from .endogenous import EndogenousStimulus, EndogenousThoughtGenerator
from .global_workspace import GlobalWorkspace
from .reasoning import ReasonRequest, default_reasoner
from .replay import ReplayConsolidationEngine
from .self_model import SelfModel

@dataclass
class MindPolicy:
    phase: str = "uninitialized"
    prefer_consolidation: bool = False
    suppress_new_curiosity: bool = False
    max_new_tasks: int = 3
    overload: float = 0.0
    def as_dict(self) -> dict[str, Any]:
        return {"phase": self.phase, "prefer_consolidation": self.prefer_consolidation,
                "suppress_new_curiosity": self.suppress_new_curiosity, "max_new_tasks": self.max_new_tasks,
                "overload": self.overload}

@dataclass
class NightPhaseResult:
    phase: str
    consolidated: int = 0
    hypotheses: int = 0
    replayed: int = 0
    notes: list[str] = field(default_factory=list)

class MindRuntime:
    def __init__(self) -> None:
        self.generator = EndogenousThoughtGenerator()
        self.reasoner = default_reasoner()
        self.workspace = GlobalWorkspace()
        self.self_model = SelfModel()
        self.curiosity = CuriosityEngine()
        self.replay = ReplayConsolidationEngine()
        self.policy = MindPolicy()
        self._reason_calls = 0
        self._curiosity_resolved = 0
        self._outcomes: list[Any] = []
        self._active_focus: str | None = None

    def next_endogenous_stimulus(self, *, beliefs=None, working_memory_items=None,
                                  self_status=None, circadian_phase=None, open_contradictions=None) -> EndogenousStimulus | None:
        if self.policy.suppress_new_curiosity and self.policy.prefer_consolidation:
            pass
        prefer = None
        if self._active_focus:
            prefer = "curiosity"
        thought = self.generator.next_thought(
            beliefs=beliefs or [], working_memory=working_memory_items or [],
            open_contradictions=list(open_contradictions or []),
            self_status=self_status or self.status(), prefer_kind=prefer)
        if thought is None:
            return None
        if thought.kind in ("curiosity", "contradiction", "dream"):
            task = {"curiosity": "curiosity_answer", "contradiction": "contradiction", "dream": "dream_skeptic"}[thought.kind]
            try:
                result = self.reasoner.reason(ReasonRequest(
                    task_type=task, prompt=thought.claim,
                    context={"question": thought.claim, "hypothesis": thought.claim,
                             "belief_statements": [getattr(b, "statement", str(b)) for b in (beliefs or [])[:5]],
                             "dream_confidence": 0.5}))
                self._reason_calls += 1
                thought.content = result.content
                thought.metadata = {**(thought.metadata or {}), "reasoner": result.model_id, "confidence": result.confidence}
            except Exception:
                pass
        if thought.kind == "curiosity" and not self.policy.suppress_new_curiosity:
            try:
                self.curiosity.open_task(thought.claim)
            except Exception:
                pass
        return thought

    def try_auto_resolve_from_claim(self, claim: str, content: str) -> None:
        try:
            if content and len(content) > 40 and "Question under investigation" in content:
                self.curiosity.resolve_task(claim, content[:500])
                self._curiosity_resolved += 1
        except Exception:
            pass

    def broadcast_focus(self, *, title: str, content: str, salience: float = 0.5,
                        novelty: float = 0.5, urgency: float = 0.3, source_refs=None) -> Any:
        try:
            item = self.workspace.broadcast(title=title, content=content, salience=salience,
                novelty=novelty, urgency=urgency, source_refs=list(source_refs or []))
            self._active_focus = title
            return item
        except Exception:
            class _Item:
                def __init__(self): self.id = str(uuid4())
            item = _Item()
            if not hasattr(self.workspace, "items"):
                self.workspace.items = {}
            self.workspace.items[item.id] = item
            self._active_focus = title
            return item

    def refresh_policy(self, *, belief_count: int = 0, open_curiosity: int = 0, overload_hint: float = 0.0) -> MindPolicy:
        overload = max(0.0, min(1.0, overload_hint + 0.05 * max(0, open_curiosity - 3)))
        self.policy.overload = overload
        self.policy.phase = "active" if belief_count else "uninitialized"
        self.policy.prefer_consolidation = overload >= 0.6
        self.policy.suppress_new_curiosity = overload >= 0.75
        self.policy.max_new_tasks = 1 if overload >= 0.6 else 3
        return self.policy

    def run_night_phase(self, *, circadian_phase=None, beliefs=None, event_store=None) -> NightPhaseResult | None:
        phase_name = str(getattr(circadian_phase, "value", circadian_phase) or "nrem").lower()
        if "rem" in phase_name and "nrem" not in phase_name:
            result = NightPhaseResult(phase="rem", hypotheses=min(3, len(list(beliefs or []))))
        else:
            replayed = 0
            if self._outcomes:
                try:
                    self.replay.consolidate(self._outcomes[-10:])
                    replayed = len(self._outcomes[-10:])
                except Exception:
                    pass
            result = NightPhaseResult(phase="nrem", consolidated=len(list(beliefs or [])), replayed=replayed)
        if event_store is not None and hasattr(event_store, "append"):
            try:
                from .events import BrainEvent
                event_store.append(BrainEvent("dream.night_phase", "mind", uuid4(), {
                    "phase": result.phase, "consolidated": result.consolidated,
                    "hypotheses": result.hypotheses, "replayed": result.replayed}))
            except Exception:
                pass
        return result

    def buffer_outcome(self, outcome: Any) -> None:
        self._outcomes.append(outcome)

    def curiosity_open_count(self) -> int:
        try:
            return len(getattr(self.curiosity, "open_tasks", lambda: [])() or [])
        except Exception:
            return 0

    def status(self) -> dict[str, Any]:
        ws = {}
        try:
            ws = self.workspace.snapshot() if hasattr(self.workspace, "snapshot") else {"workspace_items": len(getattr(self.workspace, "items", {}))}
        except Exception:
            ws = {}
        return {
            "reason_calls": self._reason_calls,
            "curiosity_resolved": self._curiosity_resolved,
            "outcomes_buffered": len(self._outcomes),
            "policy": self.policy.as_dict(),
            "workspace": ws,
            "active_focus": self._active_focus,
        }
