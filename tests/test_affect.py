from brain.affect import AffectAppraisalService, AppraisalInput, DiscreteEmotion
from brain.cognitive_state import NeuromodulatorState


def test_joy_from_positive_congruent_event():
    svc = AffectAppraisalService()
    emotion = svc.appraise(
        AppraisalInput(
            goal_congruence=0.9,
            novelty=0.3,
            urgency=0.2,
            controllability=0.7,
            certainty=0.8,
        )
    )
    assert emotion.valence > 0
    assert emotion.label in {DiscreteEmotion.JOY, DiscreteEmotion.INTEREST, DiscreteEmotion.RELIEF, DiscreteEmotion.PRIDE}


def test_fear_from_urgent_uncontrollable_threat():
    svc = AffectAppraisalService()
    emotion = svc.appraise(
        AppraisalInput(
            goal_congruence=-0.8,
            novelty=0.6,
            urgency=0.9,
            controllability=0.1,
            certainty=0.4,
        )
    )
    assert emotion.valence < 0
    assert emotion.label == DiscreteEmotion.FEAR


def test_mood_biases_subsequent_appraisal():
    svc = AffectAppraisalService()
    for _ in range(5):
        svc.appraise(
            AppraisalInput(
                goal_congruence=0.9,
                novelty=0.2,
                urgency=0.2,
                controllability=0.7,
                certainty=0.8,
            )
        )
    assert svc.mood.valence > 0


def test_modulator_delta_stress_on_negative_arousal():
    svc = AffectAppraisalService()
    emotion = svc.appraise(
        AppraisalInput(
            goal_congruence=-0.7,
            novelty=0.5,
            urgency=0.8,
            controllability=0.2,
            certainty=0.3,
        )
    )
    delta = svc.modulator_delta(emotion)
    assert isinstance(delta, NeuromodulatorState)
    assert delta.stress >= 0.2


def test_memory_salience_boost_scales_with_intensity():
    svc = AffectAppraisalService()
    mild = svc.appraise(
        AppraisalInput(
            goal_congruence=0.2,
            novelty=0.1,
            urgency=0.1,
            controllability=0.5,
            certainty=0.9,
        )
    )
    strong = svc.appraise(
        AppraisalInput(
            goal_congruence=-0.9,
            novelty=0.8,
            urgency=0.9,
            controllability=0.1,
            certainty=0.2,
        )
    )
    assert svc.memory_salience_boost(strong) >= svc.memory_salience_boost(mild)


def test_clamp_bounds_inputs():
    a = AppraisalInput(
        goal_congruence=5.0,
        novelty=-1.0,
        urgency=2.0,
        controllability=-0.5,
        certainty=1.5,
        norm_compatibility=-3.0,
    ).clamp()
    assert a.goal_congruence == 1.0
    assert a.novelty == 0.0
    assert a.urgency == 1.0
    assert a.controllability == 0.0
    assert a.certainty == 1.0
    assert a.norm_compatibility == -1.0
