"""Mind runtime — endogenous loop, GWT gate, policy, night phase, reasoner."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .curiosity import CuriosityEngine, CuriosityState
from .dreaming import ReplayConsolidationEngine
from .endogenous import EndogenousStimulus, EndogenousThoughtGenerator
from .global_workspace import GlobalWorkspace, GlobalWorkspaceItem
from .reasoning import ReasonRequest, default_reasoner
from .self_model import SelfModel


@dataclass
class MindPolicy:
    phase: str = "uninitialized"
    prefer_consolidation: bool = False
    suppress_new_curiosity: bool = False
    max_new_tasks: int = 3
    overload: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "prefer_consolidation": self.prefer_consolidation,
            "suppress_new_curiosity": self.suppress_new_curiosity,
            "max_new_tasks": self.max_new_tasks,
            "overload": self.overload,
        }


@dataclass
class NightPhaseResult:
    phase: str
    consolidated: int = 0
    hypotheses: int = 0
    replayed: int = 0
    notes: list[str] = field(default_factory=list)


class MindRuntime:
    """Orchestrates endogenous thought, GWT focus, policy, and sleep replay."""

    def __init__(self) -> None:
        self.generator = EndogenousThoughtGenerator()
        self.reasoner = default_reasoner()
        self.workspace = GlobalWorkspace()
        self.self_model = SelfModel()
        self.curiosity = CuriosityEngine()
        self._replay: ReplayConsolidationEngine | None = None
        self.policy = MindPolicy()
        self._reason_calls = 0
        self._curiosity_resolved = 0
        self._outcomes: list[Any] = []
        self._active_focus: str | None = None

    def _get_replay(self) -> ReplayConsolidationEngine | None:
        if self._replay is not None:
            return self._replay
        try:
            from .attribution import OutcomeAttribution

            self._replay = ReplayConsolidationEngine(OutcomeAttribution())
        except Exception:
            self._replay = None
        return self._replay

    def next_endogenous_stimulus(
        self,
        *,
        beliefs=None,
        working_memory_items=None,
        self_status=None,
        circadian_phase=None,
        open_contradictions=None,
    ) -> EndogenousStimulus | None:
        prefer = "curiosity" if self._active_focus else None
        if self.policy.suppress_new_curiosity:
            prefer = "contradiction"

        thought = self.generator.next_thought(
            beliefs=beliefs or [],
            working_memory_items=working_memory_items or None,
            self_status=self_status or self.status(),
            open_contradictions=list(open_contradictions or []),
            prefer_kind=prefer,
        )
        if thought is None:
            return None

        if thought.kind in ("curiosity", "contradiction", "dream", "bootstrap"):
            task_map = {
                "curiosity": "curiosity_answer",
                "contradiction": "contradiction",
                "dream": "dream_skeptic",
                "bootstrap": "general",
            }
            task = task_map.get(thought.kind, "general")
            try:
                result = self.reasoner.reason(
                    ReasonRequest(
                        task_type=task,
                        prompt=thought.claim,
                        context={
                            "question": thought.claim,
                            "statement": thought.claim,
                            "hypothesis": thought.claim,
                            "belief_statements": [
                                getattr(b, "statement", str(b)) for b in (beliefs or [])[:5]
                            ],
                            "dream_confidence": float((thought.metadata or {}).get("dream_confidence") or 0.5),
                        },
                    )
                )
                self._reason_calls += 1
                thought.content = result.content
                thought.metadata = {
                    **(thought.metadata or {}),
                    "reasoner": result.model_id,
                    "confidence": result.confidence,
                }
            except Exception:
                pass

        if thought.kind == "curiosity" and not self.policy.suppress_new_curiosity:
            try:
                open_count = sum(
                    1
                    for t in self.curiosity.tasks
                    if t.state
                    in {
                        CuriosityState.GENERATED,
                        CuriosityState.PRIORITIZED,
                        CuriosityState.INVESTIGATING,
                    }
                )
                if open_count < self.policy.max_new_tasks:
                    self.curiosity.generate(
                        "endogenous",
                        ["endogenous"],
                        thought.claim,
                        expected_value=0.55,
                        uncertainty=0.7,
                        cost=0.15,
                    )
            except Exception:
                pass

        return thought

    def try_auto_resolve_from_claim(self, claim: str, content: str) -> None:
        if not content or len(content) < 40:
            return
        try:
            for task in self.curiosity.tasks:
                if task.state in {
                    CuriosityState.GENERATED,
                    CuriosityState.PRIORITIZED,
                    CuriosityState.INVESTIGATING,
                } and (claim in task.question or task.question in claim):
                    task.state = CuriosityState.ANSWERED
                    self._curiosity_resolved += 1
        except Exception:
            pass

    def broadcast_focus(
        self,
        *,
        title: str,
        content: str,
        salience: float = 0.5,
        novelty: float = 0.5,
        urgency: float = 0.3,
        source_refs=None,
    ) -> Any:
        item = GlobalWorkspaceItem(
            item_type="endogenous_thought",
            title=title[:200],
            content=content[:2000],
            source_refs=list(source_refs or ["endogenous"]),
            salience=float(salience),
            novelty=float(novelty),
            urgency=float(urgency),
        )
        try:
            admitted = self.workspace.consider(item)
            if admitted or item.focus_score >= 0.3:
                self._active_focus = title
            return item
        except Exception:
            self._active_focus = title
            return item

    def refresh_policy(
        self,
        *,
        belief_count: int = 0,
        open_curiosity: int = 0,
        overload_hint: float = 0.0,
    ) -> MindPolicy:
        try:
            snap = self.self_model.current()
            if snap is not None:
                load = float(getattr(snap, "cognitive_load", None) or getattr(snap, "load", 0) or 0)
                overload_hint = max(overload_hint, load)
        except Exception:
            pass

        overload = max(0.0, min(1.0, overload_hint + 0.05 * max(0, open_curiosity - 3)))
        self.policy.overload = overload
        self.policy.phase = "active" if belief_count else "uninitialized"
        self.policy.prefer_consolidation = overload >= 0.6
        self.policy.suppress_new_curiosity = overload >= 0.75
        self.policy.max_new_tasks = 1 if overload >= 0.6 else 3
        return self.policy

    def run_night_phase(
        self, *, circadian_phase=None, beliefs=None, event_store=None
    ) -> NightPhaseResult | None:
        phase_name = str(getattr(circadian_phase, "value", circadian_phase) or "nrem").lower()
        if "rem" in phase_name and "nrem" not in phase_name:
            result = NightPhaseResult(phase="rem", hypotheses=min(3, len(list(beliefs or []))))
        else:
            replayed = 0
            engine = self._get_replay()
            if engine is not None and self._outcomes:
                try:
                    eng_result = engine.consolidate(
                        list(self._outcomes[-10:]),
                        edges_by_outcome={},
                    )
                    replayed = len(getattr(eng_result, "replayed_outcome_ids", None) or self._outcomes[-10:])
                except Exception:
                    replayed = 0
            result = NightPhaseResult(
                phase="nrem",
                consolidated=len(list(beliefs or [])),
                replayed=replayed,
            )

        if event_store is not None and hasattr(event_store, "append"):
            try:
                from .events import BrainEvent

                event_store.append(
                    BrainEvent(
                        "dream.night_phase",
                        "mind",
                        uuid4(),
                        {
                            "phase": result.phase,
                            "consolidated": result.consolidated,
                            "hypotheses": result.hypotheses,
                            "replayed": result.replayed,
                        },
                    )
                )
            except Exception:
                pass
        return result

    def buffer_outcome(self, outcome: Any) -> None:
        self._outcomes.append(outcome)

    def curiosity_open_count(self) -> int:
        try:
            return sum(
                1
                for t in self.curiosity.tasks
                if t.state
                in {
                    CuriosityState.GENERATED,
                    CuriosityState.PRIORITIZED,
                    CuriosityState.INVESTIGATING,
                }
            )
        except Exception:
            return 0

    def status(self) -> dict[str, Any]:
        ws: dict[str, Any] = {}
        try:
            ws = self.workspace.snapshot()
        except Exception:
            ws = {"workspace_items": len(getattr(self.workspace, "items", {}))}
        focus = []
        try:
            focus = [getattr(i, "title", str(i)) for i in self.workspace.active_focus()[:5]]
        except Exception:
            pass
        return {
            "reason_calls": self._reason_calls,
            "curiosity_resolved": self._curiosity_resolved,
            "outcomes_buffered": len(self._outcomes),
            "policy": self.policy.as_dict(),
            "workspace": ws,
            "active_focus": self._active_focus,
            "focus_titles": focus,
        }
