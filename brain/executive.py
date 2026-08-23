"""Executive control.

Real brains do not act on whatever response fires strongest. Prefrontal
cortex -- especially anterior cingulate (conflict monitoring) and
dorsolateral PFC (inhibition/goal maintenance) -- can veto a fast, strongly
triggered "prepotent" response in favor of a slower one that actually serves
current goals. This is the classic Stroop / go-no-go / delay-of-gratification
circuit, and it is finite: overriding a prepotent response draws on a
depletable control resource (the "ego depletion" literature), and that
resource's effectiveness is itself modulated by stress and acetylcholine.

Nothing in this repo currently does this. ``WorkingMemory`` holds candidate
content but nothing arbitrates between competing candidates when they
disagree, and nothing can fail to override a bad-but-strong impulse the way
a real, resource-limited controller can. This module is that missing
arbitration layer. It is domain-neutral: it knows nothing about
opportunities or money paths, the same way ``brain/affect.py`` doesn't.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from .cognitive_state import CognitiveDrive, NeuromodulatorState
from .domain import utcnow


class ResponseSource(StrEnum):
    """Where a candidate response came from -- mirrors the dual-process
    (habitual/fast vs. deliberate/slow) framing used throughout cognitive
    neuroscience of action selection."""

    HABITUAL = "habitual"
    DELIBERATE = "deliberate"


@dataclass(slots=True)
class ResponseCandidate:
    """One option competing for selection.

    prepotency: how strongly this response is triggered by the stimulus
        itself, independent of whether it's a good idea [0, 1]. A habitual
        response to a familiar cue has high prepotency by construction.
    goal_alignment: how well this response serves active goals [-1, 1].
    expected_value: the organism's estimate of payoff if executed.
    """

    action: str
    source: ResponseSource
    prepotency: float
    goal_alignment: float
    expected_value: float
    payload: dict[str, object] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)

    @property
    def goal_score(self) -> float:
        return self.goal_alignment * (0.5 + 0.5 * abs(self.expected_value))


@dataclass(slots=True)
class ConflictSignal:
    """Output of conflict monitoring -- the ACC's job. High conflict means
    the prepotent response and the goal-best response disagree, which is
    exactly the situation that requires (and consumes) control."""

    magnitude: float  # [0, 1]
    prepotent: ResponseCandidate
    goal_best: ResponseCandidate


class ConflictMonitor:
    """Detects disagreement between what's strongly triggered and what's
    actually goal-congruent, the way a Stroop trial detects disagreement
    between word-reading and color-naming responses."""

    def evaluate(self, candidates: list[ResponseCandidate]) -> ConflictSignal:
        if not candidates:
            raise ValueError("conflict_monitor_requires_candidates")
        prepotent = max(candidates, key=lambda c: c.prepotency)
        goal_best = max(candidates, key=lambda c: c.goal_score)
        if prepotent.id == goal_best.id:
            magnitude = 0.0
        else:
            disagreement = abs(prepotent.goal_score - goal_best.goal_score)
            magnitude = max(0.0, min(1.0, prepotent.prepotency * disagreement))
        return ConflictSignal(magnitude=magnitude, prepotent=prepotent, goal_best=goal_best)


@dataclass(slots=True)
class CognitiveControlResource:
    """Finite, depletable capacity to override prepotent responses.

    This is the mechanistic reason willpower fails under load in the
    ego-depletion literature: it's a resource, not a switch. It depletes
    with use proportional to conflict magnitude, and recovers with rest
    (call ``recover`` from the same cycle/tick machinery that already
    drives ``HomeostasisEngine`` and ``SleepConsolidationService``).
    """

    capacity: float = 1.0
    current: float = 1.0
    recovery_rate: float = 0.05
    updated_at: object = field(default_factory=utcnow)

    @property
    def depletion_ratio(self) -> float:
        return 1.0 - (self.current / self.capacity if self.capacity else 0.0)

    def spend(self, amount: float) -> CognitiveControlResource:
        self.current = max(0.0, self.current - max(0.0, amount))
        self.updated_at = utcnow()
        return self

    def recover(self, ticks: float = 1.0) -> CognitiveControlResource:
        self.current = min(self.capacity, self.current + self.recovery_rate * ticks)
        self.updated_at = utcnow()
        return self


@dataclass(slots=True)
class ExecutiveDecision:
    chosen: ResponseCandidate
    conflict: ConflictSignal
    override_attempted: bool
    override_succeeded: bool
    control_cost: float
    effective_control: float
    id: UUID = field(default_factory=uuid4)


@dataclass
class ExecutiveControlService:
    """The arbiter. Given competing candidates, current goals, the
    control resource, and neuromodulator state, decides what actually
    gets to happen -- and honestly reports when it *couldn't* stop an
    impulsive response because the resource or the modulatory state
    didn't support it, rather than silently pretending control always wins.
    """

    conflict_monitor: ConflictMonitor = field(default_factory=ConflictMonitor)

    def _effective_control(self, modulation: NeuromodulatorState) -> float:
        """Acetylcholine sharpens top-down attention/control; stress and
        very high norepinephrine push behavior toward fast/reflexive
        responding at the expense of deliberation -- both well-established
        directions of effect, not just symmetric noise."""
        control = 0.5 + 0.6 * modulation.acetylcholine
        control -= 0.5 * modulation.stress
        control -= 0.2 * max(0.0, modulation.norepinephrine - 0.7)
        return max(0.05, min(1.0, control))

    def arbitrate(
        self,
        candidates: list[ResponseCandidate],
        *,
        goals: list[CognitiveDrive] | None,
        control: CognitiveControlResource,
        modulation: NeuromodulatorState,
    ) -> ExecutiveDecision:
        conflict = self.conflict_monitor.evaluate(candidates)

        if conflict.magnitude <= 0.0:
            # No conflict: the strongest impulse already is the goal-best
            # option. No control resource is spent -- this mirrors how
            # effortless, non-conflicted responding costs little PFC
            # engagement in practice.
            return ExecutiveDecision(
                chosen=conflict.goal_best,
                conflict=conflict,
                override_attempted=False,
                override_succeeded=False,
                control_cost=0.0,
                effective_control=self._effective_control(modulation),
            )

        effective_control = self._effective_control(modulation)
        # Overriding a prepotent response costs control proportional to how
        # strong the impulse is and how much goals demand a different
        # answer, discounted by how effective control currently is (fatigued
        # or stressed control spends more for the same result).
        goal_pressure = 1.0
        if goals:
            goal_pressure = 1.0 + 0.5 * min(1.0, sum(g.deficit for g in goals))
        raw_cost = conflict.magnitude * goal_pressure
        # Effective control acts as a discount on cost, not a divisor: a
        # well-regulated controller (high acetylcholine, low stress) pays
        # less to win the same override than a fatigued/stressed one, but
        # cost stays bounded so override is never structurally impossible
        # for a fully-resourced controller.
        cost = raw_cost * (1.2 - effective_control)

        can_override = control.current >= cost
        if can_override:
            control.spend(cost)
            return ExecutiveDecision(
                chosen=conflict.goal_best,
                conflict=conflict,
                override_attempted=True,
                override_succeeded=True,
                control_cost=cost,
                effective_control=effective_control,
            )

        # Control resource insufficient: spend whatever remains (a failed,
        # exhausting attempt still costs something -- you don't get an
        # override for free just because it failed) and fall back to the
        # prepotent response. This is the impulsive-choice failure mode.
        spent = control.current
        control.spend(spent)
        return ExecutiveDecision(
            chosen=conflict.prepotent,
            conflict=conflict,
            override_attempted=True,
            override_succeeded=False,
            control_cost=spent,
            effective_control=effective_control,
        )
