"""Theory of mind: model other agents' beliefs, goals, and predicted behavior.

Domain-neutral service for attributed mental states. Does not emit BrainEvents
or wire into the continuous cognition runner in this slice (HOLD).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AttributedBelief:
    """What the Brain believes an agent believes (may diverge from ground truth)."""

    agent_id: str
    statement: str
    confidence: float
    evidence_refs: list[str]
    updated_at: datetime = field(default_factory=_utcnow)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class AttributedGoal:
    agent_id: str
    statement: str
    confidence: float
    evidence_refs: list[str]
    updated_at: datetime = field(default_factory=_utcnow)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class PredictionRecord:
    agent_id: str
    predicted_action: str
    resolved: bool = False
    correct: bool | None = None
    actual_action: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class AgentModel:
    agent_id: str
    trust: float = 0.5
    beliefs: list[AttributedBelief] = field(default_factory=list)
    goals: list[AttributedGoal] = field(default_factory=list)
    predictions: list[PredictionRecord] = field(default_factory=list)

    @property
    def prediction_accuracy(self) -> float:
        resolved = [p for p in self.predictions if p.resolved and p.correct is not None]
        if not resolved:
            return 0.0
        return sum(1 for p in resolved if p.correct) / len(resolved)


@dataclass
class FalseBeliefResult:
    agent_id: str
    statement: str
    agent_believes: bool
    ground_truth: bool
    is_false_belief: bool


class TheoryOfMindService:
    """Domain-neutral theory-of-mind modeling for other agents."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentModel] = {}

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
            raise ValueError("attributed belief requires evidence_refs")
        confidence = max(0.0, min(1.0, float(confidence)))
        model = self.get_or_create(agent_id)
        belief = AttributedBelief(
            agent_id=agent_id,
            statement=statement,
            confidence=confidence,
            evidence_refs=list(evidence_refs),
        )
        model.beliefs.append(belief)
        return belief

    def infer_goal(
        self,
        agent_id: str,
        *,
        statement: str,
        confidence: float,
        evidence_refs: list[str],
    ) -> AttributedGoal:
        if not evidence_refs:
            raise ValueError("attributed goal requires evidence_refs")
        confidence = max(0.0, min(1.0, float(confidence)))
        model = self.get_or_create(agent_id)
        goal = AttributedGoal(
            agent_id=agent_id,
            statement=statement,
            confidence=confidence,
            evidence_refs=list(evidence_refs),
        )
        model.goals.append(goal)
        return goal

    def check_false_belief(
        self,
        agent_id: str,
        statement: str,
        *,
        ground_truth: bool,
    ) -> FalseBeliefResult:
        model = self.get_or_create(agent_id)
        matches = [
            b
            for b in model.beliefs
            if b.statement.strip().lower() == statement.strip().lower()
        ]
        agent_believes = bool(matches) and max(b.confidence for b in matches) >= 0.5
        return FalseBeliefResult(
            agent_id=agent_id,
            statement=statement,
            agent_believes=agent_believes,
            ground_truth=ground_truth,
            is_false_belief=agent_believes and not ground_truth,
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t for t in text.lower().replace("-", " ").split() if t}

    def predict_action(
        self,
        agent_id: str,
        candidates: list[str],
    ) -> tuple[str, float]:
        if not candidates:
            raise ValueError("candidates required")
        model = self.get_or_create(agent_id)
        goal_tokens: set[str] = set()
        for g in model.goals:
            goal_tokens |= self._tokens(g.statement)
            weight = g.confidence
            # expand with weight via multiplicity (simple)
            if weight >= 0.75:
                goal_tokens |= self._tokens(g.statement)

        best = candidates[0]
        best_score = -1.0
        for cand in candidates:
            ct = self._tokens(cand)
            if not ct:
                score = 0.0
            else:
                score = len(goal_tokens & ct) / len(ct)
            if score > best_score:
                best_score = score
                best = cand

        # Confidence from overlap * trust; zero overlap => zero confidence
        confidence = max(0.0, min(1.0, best_score * model.trust))
        return best, confidence

    def record_prediction(self, agent_id: str, predicted_action: str) -> PredictionRecord:
        model = self.get_or_create(agent_id)
        rec = PredictionRecord(agent_id=agent_id, predicted_action=predicted_action)
        model.predictions.append(rec)
        return rec

    def resolve_prediction(
        self,
        agent_id: str,
        record: PredictionRecord,
        *,
        actual_action: str,
    ) -> AgentModel:
        model = self.get_or_create(agent_id)
        record.resolved = True
        record.actual_action = actual_action
        record.correct = (
            record.predicted_action.strip().lower() == actual_action.strip().lower()
        )
        # Slow exponential blend of trust
        target = 1.0 if record.correct else 0.0
        model.trust = max(0.0, min(1.0, model.trust * 0.85 + target * 0.15))
        return model
