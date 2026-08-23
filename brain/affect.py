"""Affect / emotion system.

Real brains do not modulate behavior from raw event features directly (the
existing ``AttentionMarket`` and ``RewardSystem`` do this, and they are
domain-specific to commercial signals). Between perception and action sits an
appraisal layer -- limbic circuitry (amygdala, insula, OFC) that evaluates
*what an event means for the organism* and produces a felt state (valence,
arousal) that colors memory, attention, and decision-making generically.

This module is that layer. It is deliberately domain-neutral: it knows
nothing about opportunities or money paths. Anything in the Brain -- economic
or otherwise -- can appraise an event through it and get back an emotional
state plus a neuromodulator delta.

Grounded in Scherer's Component Process Model of appraisal: an event is
evaluated along a small number of checks, and the *pattern* of checks
determines the discrete emotion, not a single scalar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from .cognitive_state import NeuromodulatorState
from .domain import utcnow


class DiscreteEmotion(StrEnum):
    JOY = "joy"
    INTEREST = "interest"
    RELIEF = "relief"
    PRIDE = "pride"
    FEAR = "fear"
    ANGER = "anger"
    FRUSTRATION = "frustration"
    SADNESS = "sadness"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    BOREDOM = "boredom"
    NEUTRAL = "neutral"


@dataclass(slots=True)
class AppraisalInput:
    goal_congruence: float
    novelty: float
    urgency: float
    controllability: float
    certainty: float
    agency: str = "circumstance"
    norm_compatibility: float = 0.0

    def clamp(self) -> AppraisalInput:
        self.goal_congruence = max(-1.0, min(1.0, self.goal_congruence))
        self.novelty = max(0.0, min(1.0, self.novelty))
        self.urgency = max(0.0, min(1.0, self.urgency))
        self.controllability = max(0.0, min(1.0, self.controllability))
        self.certainty = max(0.0, min(1.0, self.certainty))
        self.norm_compatibility = max(-1.0, min(1.0, self.norm_compatibility))
        return self


@dataclass(slots=True)
class EmotionalState:
    valence: float
    arousal: float
    dominance: float
    label: DiscreteEmotion
    intensity: float
    source_appraisal: AppraisalInput
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


@dataclass(slots=True)
class Mood:
    valence: float = 0.0
    arousal_baseline: float = 0.3
    momentum: float = 0.9

    def integrate(self, emotion: EmotionalState) -> Mood:
        w = (1 - self.momentum) * emotion.intensity
        self.valence = self.momentum * self.valence + w * emotion.valence
        self.arousal_baseline = self.momentum * self.arousal_baseline + w * emotion.arousal
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal_baseline = max(0.0, min(1.0, self.arousal_baseline))
        return self

    def appraisal_bias(self) -> float:
        return 0.3 * self.valence


def _classify(appraisal: AppraisalInput, valence: float, arousal: float) -> DiscreteEmotion:
    if appraisal.novelty > 0.75 and abs(appraisal.goal_congruence) < 0.2:
        return DiscreteEmotion.SURPRISE
    if valence >= 0.15:
        if appraisal.urgency < 0.3 and appraisal.novelty > 0.4:
            return DiscreteEmotion.INTEREST
        if appraisal.agency == "self" and appraisal.goal_congruence > 0.5:
            return DiscreteEmotion.PRIDE
        if appraisal.controllability < 0.3:
            return DiscreteEmotion.RELIEF
        return DiscreteEmotion.JOY
    if valence <= -0.15:
        if appraisal.norm_compatibility < -0.3:
            return DiscreteEmotion.DISGUST
        if appraisal.controllability < 0.3 and appraisal.urgency > 0.5:
            return DiscreteEmotion.FEAR
        if appraisal.agency in ("other", "self") and appraisal.controllability >= 0.3:
            return DiscreteEmotion.ANGER
        if appraisal.controllability >= 0.3 and appraisal.urgency > 0.4:
            return DiscreteEmotion.FRUSTRATION
        if arousal < 0.35:
            return DiscreteEmotion.SADNESS
        return DiscreteEmotion.FRUSTRATION
    if arousal < 0.15 and appraisal.novelty < 0.2:
        return DiscreteEmotion.BOREDOM
    return DiscreteEmotion.NEUTRAL


@dataclass
class AffectAppraisalService:
    mood: Mood = field(default_factory=Mood)
    history: list[EmotionalState] = field(default_factory=list)
    max_history: int = 500

    def appraise(self, appraisal: AppraisalInput) -> EmotionalState:
        appraisal = appraisal.clamp()
        biased_congruence = max(-1.0, min(1.0, appraisal.goal_congruence + self.mood.appraisal_bias()))
        valence = 0.75 * biased_congruence + 0.25 * appraisal.norm_compatibility
        valence = max(-1.0, min(1.0, valence))
        arousal = 0.5 * appraisal.novelty + 0.5 * appraisal.urgency
        arousal *= 1.0 - 0.3 * appraisal.certainty
        arousal = max(0.0, min(1.0, arousal + 0.15 * self.mood.arousal_baseline))
        dominance = appraisal.controllability
        intensity = max(0.0, min(1.0, arousal * (0.4 + 0.6 * abs(valence))))
        label = _classify(appraisal, valence, arousal)
        emotion = EmotionalState(
            valence=valence, arousal=arousal, dominance=dominance,
            label=label, intensity=intensity, source_appraisal=appraisal,
        )
        self.mood.integrate(emotion)
        self.history.append(emotion)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        return emotion

    def modulator_delta(self, emotion: EmotionalState) -> NeuromodulatorState:
        dopamine = 0.5 + 0.5 * max(0.0, emotion.valence) * emotion.intensity
        dopamine -= 0.3 * max(0.0, -emotion.valence) * emotion.intensity
        norepinephrine = 0.4 + 0.6 * emotion.arousal
        serotonin = 0.5 + 0.4 * self.mood.valence
        acetylcholine = 0.5 + 0.3 * (1 - emotion.arousal) * max(0.0, emotion.valence)
        stress = 0.2 + 0.6 * emotion.arousal * max(0.0, -emotion.valence)
        return NeuromodulatorState(
            dopamine=dopamine, norepinephrine=norepinephrine, serotonin=serotonin,
            acetylcholine=acetylcholine, stress=stress,
        ).clamp()

    def memory_salience_boost(self, emotion: EmotionalState) -> float:
        return 0.4 * emotion.arousal * (0.5 + 0.5 * abs(emotion.valence))
