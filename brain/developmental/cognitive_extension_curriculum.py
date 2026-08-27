"""Developmental curriculum for the cognitive-extension modules.

This is the concrete answer to "teach this Brain how to be a brain, the
way an infant learns its world": not a claim that these modules feel or
understand anything, but a genuine, evidence-gated application of
``HigherOrderCognitionService``'s developmental-stage machinery
(``docs/spec/BRAIN_DEVELOPMENTAL_INTELLIGENCE_ARCHITECTURE.md``, section
4) to the seven modules built for affect, executive control, circadian
regulation, theory of mind, hedonic learning, perception, and motor
execution.

Each stage claim below is made only where a real capability exists and is
test-verified -- never by assumption, never uniformly across every module.
Skipping a stage for a given module is documented, not silent, per that
architecture doc's "No stage may be skipped silently" rule.
``HigherOrderCognitionService.enter_developmental_stage`` itself enforces
that advanced stages (METACOGNITIVE, SELF_REPAIRING) cannot be entered
without ``capabilities_unlocked`` evidence -- this module does not
duplicate that enforcement, it relies on it.

What this explicitly does NOT claim, matching
``HigherOrderCognitionService.claim_boundary_report()``'s permanently
blocked list: consciousness, subjective/phenomenal feeling, biological
neural equivalence, or that any module is "done." An appraised
``EmotionalState`` is a computed functional analog (valence/arousal from
Scherer-style appraisal checks) -- not a claim that the Brain feels
anything. The developmental-stage labels below describe capability
maturity, the same way the term is used for a software system's test
coverage or a research benchmark, not childhood development in the
literal sense -- Tyler's "infant" framing is the right intuition for
*why this staged structure exists*, not a claim that the system involved
is anything like a human infant.
"""

from __future__ import annotations

from .higher_order_cognition import (
    DevelopmentalStage,
    DevelopmentalStageRecord,
    HigherOrderCognitionService,
)

# Module path -> (stage evidence, keyed by stage). A module only appears
# under a stage where a specific, real, test-verified capability supports
# the claim. Absence from a stage is a documented "not yet" below, in
# NOT_YET_CLAIMED, not an oversight.

REFLEX_EVIDENCE: dict[str, list[str]] = {
    # reflex = "deterministic rule or fixture exists" (architecture doc,
    # stage 1). True for all seven: every one is a pure function/service
    # with deterministic, test-verified stimulus -> response behavior.
    "brain/affect.py": ["tests/test_affect.py"],
    "brain/executive.py": ["tests/test_executive.py"],
    "brain/circadian.py": ["tests/test_circadian.py"],
    "brain/theory_of_mind.py": ["tests/test_theory_of_mind.py"],
    "brain/hedonic.py": ["tests/test_hedonic.py"],
    "brain/perception.py": ["tests/test_perception.py", "tests/test_perception_image_audio.py"],
    "brain/motor.py": ["tests/test_motor.py", "tests/test_motor_http_effector.py"],
}

PERCEPTUAL_EVIDENCE: dict[str, list[str]] = {
    # perceptual = "the system can detect and normalize signals" (stage 2).
    # Only perception.py's job. Habituation normalizes repeated exposure
    # into a novelty score; NumericPerceptionEncoder z-scores against a
    # running distribution rather than reporting raw magnitude.
    "brain/perception.py": ["tests/test_perception.py::test_repeated_similar_stimulus_habituates_and_novelty_drops"],
}

ASSOCIATIVE_EVIDENCE: dict[str, list[str]] = {
    # associative = "the system links signals, beliefs, and outcomes"
    # (stage 3). Three modules genuinely accumulate cross-event links,
    # not just react to one event at a time.
    "brain/affect.py": ["tests/test_affect.py::test_mood_integrates_across_events_and_biases_future_appraisal"],
    "brain/theory_of_mind.py": ["tests/test_theory_of_mind.py::test_trust_increases_after_correct_prediction_and_decreases_after_wrong"],
    "brain/hedonic.py": ["tests/test_hedonic.py::test_repeated_identical_reward_stops_producing_positive_error_as_baseline_adapts"],
}

PREDICTIVE_EVIDENCE: dict[str, list[str]] = {
    # predictive = "the system can forecast outcomes and record error"
    # (stage 4). Three modules have an explicit prediction/error object.
    "brain/hedonic.py": ["brain/hedonic.py:RewardPredictionError", "tests/test_hedonic.py::test_positive_surprise_when_actual_beats_expected"],
    "brain/theory_of_mind.py": ["tests/test_theory_of_mind.py::test_predict_action_uses_attributed_goals_not_ground_truth"],
    "brain/motor.py": ["brain/motor.py:MotorPrediction", "tests/test_motor.py::test_repeated_overshoot_increases_gain_correction_downward"],
}

STRATEGIC_EVIDENCE: dict[str, list[str]] = {
    # strategic = "the system can compare plans under risk" (stage 5).
    # Only executive control does this: ConflictMonitor + arbitrate()
    # explicitly compare a habitual vs. a deliberate response and spend a
    # depletable, risk-like resource to choose between them.
    "brain/executive.py": [
        "tests/test_executive.py::test_full_control_resource_overrides_prepotent_impulse",
        "tests/test_executive.py::test_depleted_control_resource_falls_back_to_impulse",
    ],
}

# Explicit "not yet" -- what's missing for the three most advanced stages,
# and for the modules/stage combinations skipped above. This list IS the
# self-model output: what the system does not yet do, stated plainly.
NOT_YET_CLAIMED: list[str] = [
    "METACOGNITIVE for any module: none of the seven can currently report "
    "its own confidence/limits about ITS OWN behavior as a first-class "
    "output -- brain/developmental/self_model.py exists but is not wired "
    "to affect/executive/circadian/theory_of_mind/hedonic/perception/motor. "
    "Needed: a self-report method per module surfaced through self_model.py, "
    "with evidence that the reported uncertainty tracks actual error.",
    "SELF_REPAIRING for any module: no module currently proposes a governed "
    "change to itself. Needed: a DevelopmentalPlasticityDelta "
    "(docs/spec/DEVELOPMENTAL_PLASTICITY_MODEL.md) generated FROM one of "
    "these modules' own LearningEvents, reviewed under the existing "
    "improvement-cycle governance in brain/developmental/improvement_cycle.py.",
    "CONSOLIDATED for any module: this requires sustained real production "
    "evidence over time (repeated validated outcomes), not test-suite "
    "evidence alone -- these modules have been live in CognitiveCycle for "
    "one PR's worth of history, not a consolidation window.",
    "PERCEPTUAL for affect/executive/circadian/theory_of_mind/hedonic/motor: "
    "none of these detect or normalize raw external signals themselves -- "
    "they operate on already-perceived/appraised inputs, so this stage is "
    "not applicable to them, not skipped by oversight.",
    "ASSOCIATIVE for circadian/perception/motor: circadian's phase cycling "
    "is periodic/regulatory, not link-forming; perception's habituation is "
    "already claimed under PERCEPTUAL and not double-counted here; motor's "
    "per-effector calibration is claimed under PREDICTIVE, not associative "
    "linking.",
    "PREDICTIVE for affect/executive/circadian/perception: none of these "
    "forecast a future outcome and record the resulting error as a "
    "first-class object the way RewardPredictionError, predict_action, "
    "and MotorPrediction do.",
    "STRATEGIC for affect/circadian/theory_of_mind/hedonic/perception/motor: "
    "none of these compare multiple candidate plans against a depletable "
    "resource under risk -- that is specifically executive control's job.",
]


def build_curriculum() -> HigherOrderCognitionService:
    """Populate a fresh HigherOrderCognitionService with every stage claim
    this module can currently support with real evidence. Returns the
    service so callers can inspect ``service.stage_records`` or extend it
    (e.g. with a real curriculum_task once a metacognitive self-report
    method exists to build one against)."""
    service = HigherOrderCognitionService()

    def _enter(stage: DevelopmentalStage, module: str, evidence: list[str], capability: str) -> None:
        service.enter_developmental_stage(
            DevelopmentalStageRecord(
                stage=stage,
                entered_because=f"{module}: {capability}",
                evidence_refs=evidence,
                capabilities_unlocked=[capability],
                blocked_claims=[
                    "consciousness_claim",
                    "subjective_feeling_claim",
                    "neuroscience_equivalence_claim",
                ],
            )
        )

    for module, evidence in REFLEX_EVIDENCE.items():
        _enter(DevelopmentalStage.REFLEX, module, evidence, "deterministic_stimulus_response")
    for module, evidence in PERCEPTUAL_EVIDENCE.items():
        _enter(DevelopmentalStage.PERCEPTUAL, module, evidence, "signal_detection_and_normalization")
    for module, evidence in ASSOCIATIVE_EVIDENCE.items():
        _enter(DevelopmentalStage.ASSOCIATIVE, module, evidence, "cross_event_linkage")
    for module, evidence in PREDICTIVE_EVIDENCE.items():
        _enter(DevelopmentalStage.PREDICTIVE, module, evidence, "forecast_and_recorded_error")
    for module, evidence in STRATEGIC_EVIDENCE.items():
        _enter(DevelopmentalStage.STRATEGIC, module, evidence, "plan_comparison_under_resource_risk")

    return service


def assessment_report(service: HigherOrderCognitionService) -> dict[str, object]:
    """Summarize current stage attainment per module, plus the explicit
    not-yet list. This is the self-model surface: what the system can
    currently support a claim for, and what it plainly cannot yet."""
    by_module: dict[str, list[str]] = {}
    for record in service.stage_records.values():
        module = record.entered_because.split(":", 1)[0]
        by_module.setdefault(module, []).append(str(record.stage))
    return {
        "stages_by_module": by_module,
        "not_yet_claimed": NOT_YET_CLAIMED,
        "blocked_claims": service.claim_boundary_report()["blocked"],
    }
