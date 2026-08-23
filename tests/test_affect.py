from __future__ import annotations

from brain.affect import AffectAppraisalService, AppraisalInput, DiscreteEmotion


def test_positive_controllable_event_is_joy_or_pride() -> None:
    svc = AffectAppraisalService()
    emotion = svc.appraise(
        AppraisalInput(goal_congruence=0.8, novelty=0.2, urgency=0.1, controllability=0.9, certainty=0.9, agency="self")
    )
    assert emotion.valence > 0
    assert emotion.label in (DiscreteEmotion.JOY, DiscreteEmotion.PRIDE)


def test_same_valence_different_controllability_differentiates_fear_vs_anger() -> None:
    svc = AffectAppraisalService()
    fear = svc.appraise(
        AppraisalInput(goal_congruence=-0.7, novelty=0.5, urgency=0.8, controllability=0.1, certainty=0.5, agency="circumstance")
    )
    anger = svc.appraise(
        AppraisalInput(goal_congruence=-0.7, novelty=0.5, urgency=0.8, controllability=0.6, certainty=0.5, agency="other")
    )
    assert fear.label == DiscreteEmotion.FEAR
    assert anger.label == DiscreteEmotion.ANGER


def test_norm_violation_pulls_valence_negative_even_with_goal_success() -> None:
    svc = AffectAppraisalService()
    clean = svc.appraise(
        AppraisalInput(goal_congruence=0.9, novelty=0.1, urgency=0.1, controllability=0.9, certainty=0.9, norm_compatibility=0.0)
    )
    dirty = svc.appraise(
        AppraisalInput(goal_congruence=0.9, novelty=0.1, urgency=0.1, controllability=0.9, certainty=0.9, norm_compatibility=-1.0)
    )
    assert dirty.valence < clean.valence


def test_mood_integrates_across_events_and_biases_future_appraisal() -> None:
    svc = AffectAppraisalService()
    for _ in range(10):
        svc.appraise(AppraisalInput(goal_congruence=-0.6, novelty=0.3, urgency=0.3, controllability=0.5, certainty=0.6))
    assert svc.mood.valence < 0
    ambiguous = svc.appraise(AppraisalInput(goal_congruence=0.0, novelty=0.5, urgency=0.2, controllability=0.5, certainty=0.4))
    assert ambiguous.valence < 0


def test_modulator_delta_moves_dopamine_up_on_reward_and_stress_up_on_threat() -> None:
    svc = AffectAppraisalService()
    reward = svc.appraise(AppraisalInput(goal_congruence=0.9, novelty=0.2, urgency=0.2, controllability=0.9, certainty=0.9))
    threat = svc.appraise(AppraisalInput(goal_congruence=-0.9, novelty=0.8, urgency=0.9, controllability=0.1, certainty=0.4))
    assert svc.modulator_delta(reward).dopamine > 0.5
    assert svc.modulator_delta(threat).stress > svc.modulator_delta(reward).stress


def test_high_arousal_events_get_bigger_memory_salience_boost() -> None:
    svc = AffectAppraisalService()
    calm = svc.appraise(AppraisalInput(goal_congruence=0.5, novelty=0.05, urgency=0.05, controllability=0.9, certainty=0.95))
    intense = svc.appraise(AppraisalInput(goal_congruence=0.8, novelty=0.9, urgency=0.9, controllability=0.5, certainty=0.5))
    assert svc.memory_salience_boost(intense) > svc.memory_salience_boost(calm)


def test_appraisal_clamps_out_of_range_inputs() -> None:
    a = AppraisalInput(goal_congruence=5.0, novelty=-3.0, urgency=2.0, controllability=-1.0, certainty=10.0, norm_compatibility=-9.0).clamp()
    assert a.goal_congruence == 1.0
    assert a.novelty == 0.0
    assert a.controllability == 0.0
    assert a.norm_compatibility == -1.0
