"""Theory of mind / social cognition.

``brain/developmental/theory_registry.py`` tracks competing *scientific*
explanations for unknown mechanisms -- it has nothing to do with modeling
other minds. Nowhere in this repo does the Brain represent what another
agent (a counterparty, an operator, a competitor) believes, wants, or is
likely to do next, distinct from what the Brain itself believes is true.

That distinction is the entire point of theory of mind: an agent model
must be able to diverge from ground truth. The classic test (Sally-Anne /
false-belief task) is whether a system can predict someone will act on
their own (possibly wrong) belief rather than on reality. This module
makes that representable and gives the Brain a mechanism to predict other
agents' behavior from attributed beliefs/goals, and to update trust in its
own model of an agent based on whether predictions land.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .domain import utcnow


@dataclass(slots=True)
class AttributedBelief:
    """What the Brain believes *another agent* believes -- which may be
    false relative to the Brain's own ground-truth belief state. This is
    the nested-belief structure a real theory-of-mind representation
    requires and that a flat belief store cannot express."""

    statement: str
    believed_confidence: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    attributed_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class AgentGoalHypothesis:
    statement: str
    confidence: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PredictionRecord:
    predicted_action: str
    actual_action: str | None
    correct: bool | None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class AgentModel:
    """Everything the Brain currently believes about one other agent.

    trust: confidence in this model's own predictive accuracy, distinct
    from confidence in any individual belief/goal -- a model can be
    internally confident but historically unreliable, and trust should
    reflect the track record, not the model's self-assessment.
    """

    agent_id: str
    attributed_beliefs: dict[str, AttributedBelief] = field(default_factory=dict)
    attributed_goals: list[AgentGoalHypothesis] = field(default_factory=list)
    trust: float = 0.5
    prediction_history: list[PredictionRecord] = field(default_factory=list)

    @property
    def prediction_accuracy(self) -> float:
        scored = [p for p in self.prediction_history if p.correct is not None]
        if not scored:
            return 0.5
        return sum(1 for p in scored if p.correct) / len(scored)


class FalseBeliefResult:
    def __init__(self, statement: str, agent_believes: bool, ground_truth: bool):
        self.statement = statement
        self.agent_believes = agent_believes
        self.ground_truth = ground_truth
        self.is_false_belief = agent_believes != ground_truth


@dataclass
class TheoryOfMindService:
    """The mentalizing engine: attribute beliefs/goals to other agents,
    predict their behavior from those attributions (not from the Brain's
    own beliefs about the world), and update trust from whether
    predictions actually land."""

    agents: dict[str, AgentModel] = field(default_factory=dict)

    def get_or_create(self, agent_id: str) -> AgentModel:
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentModel(agent_id=agent_id)
        return self.agents[agent_id]

    def attribute_belief(
        self,
        agent_id: str,
        *,
        statement: str,
        confidence: float,
        evidence_refs: list[str],
    ) -> AttributedBelief:
        if not evidence_refs:
            raise ValueError("belief_attribution_requires_evidence")
        model = self.get_or_create(agent_id)
        belief = AttributedBelief(
            statement=statement,
            believed_confidence=max(0.0, min(1.0, confidence)),
            evidence_refs=list(evidence_refs),
        )
        model.attributed_beliefs[statement] = belief
        return belief

    def infer_goal(
        self,
        agent_id: str,
        *,
        statement: str,
        confidence: float,
        evidence_refs: list[str],
    ) -> AgentGoalHypothesis:
        model = self.get_or_create(agent_id)
        goal = AgentGoalHypothesis(
            statement=statement,
            confidence=max(0.0, min(1.0, confidence)),
            evidence_refs=list(evidence_refs),
        )
        model.attributed_goals.append(goal)
        return goal

    def check_false_belief(
        self, agent_id: str, statement: str, *, ground_truth: bool
    ) -> FalseBeliefResult:
        """The Sally-Anne test, generalized: does this agent's attributed
        belief diverge from what the Brain itself takes to be true? A
        model that can only ever say "they believe what's real" has not
        implemented theory of mind, just belief-copying.
        """
        model = self.get_or_create(agent_id)
        attributed = model.attributed_beliefs.get(statement)
        agent_believes = (
            attributed.believed_confidence >= 0.5 if attributed is not None else False
        )
        return FalseBeliefResult(statement, agent_believes, ground_truth)

    def predict_action(
        self, agent_id: str, candidate_actions: list[str]
    ) -> tuple[str, float]:
        """Predict which of several candidate actions this agent will take,
        by ranking each against attributed goals -- crudely, by substring/
        keyword overlap weighted by goal confidence. This is intentionally
        simple; the point is the architecture (predict from attributed
        mental state, not ground truth), not the NLP.

        Returns (predicted_action, confidence). Confidence is scaled by
        this agent model's own track record (``trust``), so a model with a
        poor prediction history reports lower confidence even when the
        raw goal match looks strong.
        """
        if not candidate_actions:
            raise ValueError("predict_action_requires_candidates")
        model = self.get_or_create(agent_id)
        if not model.attributed_goals:
            return candidate_actions[0], 0.1 * model.trust

        scores: dict[str, float] = {a: 0.0 for a in candidate_actions}
        for action in candidate_actions:
            for goal in model.attributed_goals:
                overlap = _token_overlap(action, goal.statement)
                scores[action] += overlap * goal.confidence

        best = max(scores, key=lambda a: scores[a])
        raw_confidence = scores[best] / max(1, len(model.attributed_goals))
        confidence = max(0.0, min(1.0, raw_confidence)) * (0.4 + 0.6 * model.trust)
        return best, confidence

    def record_prediction(self, agent_id: str, predicted_action: str) -> PredictionRecord:
        model = self.get_or_create(agent_id)
        record = PredictionRecord(predicted_action=predicted_action, actual_action=None, correct=None)
        model.prediction_history.append(record)
        return record

    def resolve_prediction(
        self, agent_id: str, record: PredictionRecord, *, actual_action: str
    ) -> AgentModel:
        """Close the loop: compare what actually happened to what was
        predicted, and update trust accordingly. Trust moves slowly
        (exponential blend) so one surprising observation doesn't erase an
        otherwise-reliable model, matching how real social trust updates.

        A record can only be resolved once -- resolving it a second time
        would apply a second trust update for a single real-world outcome,
        silently double-counting it.
        """
        if record.correct is not None:
            raise ValueError("prediction_record_already_resolved")
        model = self.get_or_create(agent_id)
        record.actual_action = actual_action
        record.correct = actual_action == record.predicted_action
        blend = 0.2
        target = 1.0 if record.correct else 0.0
        model.trust = max(0.0, min(1.0, (1 - blend) * model.trust + blend * target))
        return model


def _token_overlap(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
