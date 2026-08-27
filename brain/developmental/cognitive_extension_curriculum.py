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
from .self_model import SelfModelService

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

METACOGNITIVE_EVIDENCE: dict[str, list[str]] = {
    # metacognitive = "the system can explain its limits and uncertainty"
    # (stage 6). Earned, not assumed: theory_of_mind.py's predict_action()
    # confidence was measured (Expected Calibration Error) against actual
    # accuracy across simulated agents of known predictability, across
    # five random seeds. The prior formula measured ECE ~0.16-0.22
    # (confidence moved the right direction but the number didn't mean
    # what it said). The current formula, redesigned specifically in
    # response to that measurement, measures ~0.03-0.07. This is the one
    # module, of the seven, with both a genuine self-reported confidence
    # signal AND a resolvable ground truth (predict/resolve) to check it
    # against -- which is why it is the only one claimed here.
    "brain/theory_of_mind.py": [
        "tests/test_theory_of_mind_calibration.py::test_predict_action_confidence_is_calibrated_across_five_seeds",
        "tests/test_theory_of_mind_calibration.py::test_confidence_and_accuracy_are_positively_correlated",
    ],
}

# Explicit "not yet" -- what's missing for the three most advanced stages,
# and for the modules/stage combinations skipped above. This list IS the
# self-model output: what the system does not yet do, stated plainly.
NOT_YET_CLAIMED: list[str] = [
    "METACOGNITIVE for affect/executive/circadian/hedonic/perception/motor: "
    "none of these six currently pairs a first-class self-reported "
    "confidence/uncertainty value with a resolvable ground truth the way "
    "theory_of_mind.py's predict_action/resolve_prediction does. "
    "brain/developmental/self_model.py is wired for theory_of_mind.py's "
    "predict_action calibration specifically (see build_self_model below); "
    "it is not yet wired for the other six. Needed per module: a "
    "self-reported confidence output PLUS a real outcome to check it "
    "against -- not just adding a confidence number.",
    "SELF_REPAIRING for any module: no module currently proposes a governed "
    "change to itself. Needed: a DevelopmentalPlasticityDelta "
    "(docs/spec/DEVELOPMENTAL_PLASTICITY_MODEL.md) generated FROM one of "
    "these modules' own LearningEvents, reviewed under the existing "
    "improvement-cycle governance in brain/developmental/improvement_cycle.py.",
    "CONSOLIDATED for any module: this requires sustained real production "
    "evidence over time (repeated validated outcomes), not test-suite "
    "evidence alone -- these modules have been live in CognitiveCycle for "
    "a few PRs' worth of history, not a consolidation window.",
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
    "The METACOGNITIVE claim for theory_of_mind.py itself is bounded: "
    "calibration was measured under synthetic/simulated agent behavior "
    "with designed-in predictability, not real production agent behavior. "
    "This is recorded as an explicit limitation in build_self_model()'s "
    "SelfModelService, not silently generalized to production data.",
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
    for module, evidence in METACOGNITIVE_EVIDENCE.items():
        service.enter_developmental_stage(
            DevelopmentalStageRecord(
                stage=DevelopmentalStage.METACOGNITIVE,
                entered_because=f"{module}: predict_action confidence measured calibrated (ECE) against actual accuracy across 5 seeds",
                evidence_refs=evidence,
                capabilities_unlocked=["calibrated_self_reported_confidence"],
                blocked_claims=[
                    "consciousness_claim",
                    "subjective_feeling_claim",
                    "neuroscience_equivalence_claim",
                    "production_data_calibration_claim",  # measured on synthetic agents only
                ],
            )
        )

    return service


def build_self_model() -> SelfModelService:
    """The concrete self-model surface for the one capability that has
    earned it: theory_of_mind.py's predict_action confidence. Claims the
    capability with real evidence, records the one limitation that
    matters (synthetic, not production, data), and produces an assessment
    -- this is what 'the system can explain its limits and uncertainty'
    (METACOGNITIVE) actually means here: a specific, evidenced claim next
    to a specific, stated limitation, not a vague assertion of
    self-awareness."""
    service = SelfModelService()
    service.claim_capability(
        name="theory_of_mind.predict_action_confidence_is_calibrated",
        confidence=0.8,  # high but not 1.0: five seeds, not exhaustive validation
        evidence_refs=[
            "brain/theory_of_mind.py:TheoryOfMindService.predict_action",
            "tests/test_theory_of_mind_calibration.py",
        ],
        test_refs=[
            "tests/test_theory_of_mind_calibration.py::test_predict_action_confidence_is_calibrated_across_five_seeds",
            "tests/test_theory_of_mind_calibration.py::test_confidence_and_accuracy_are_positively_correlated",
        ],
        acceptance_refs=["reports/go-hold/COGNITIVE-EXTENSION-DEVELOPMENTAL-CURRICULUM-GO-HOLD.json"],
    )
    service.record_limitation(
        limitation="predict_action calibration was measured only on simulated agents with "
        "designed-in, known predictability (90%/chance/55%), not on real production agent "
        "behavior",
        effect="the calibration claim does not generalize to production until measured there; "
        "a production calibration re-check is required before this limitation can be lifted",
    )
    service.record_limitation(
        limitation="calibration was measured for theory_of_mind.py's predict_action only -- "
        "no other module (affect, executive, circadian, hedonic, perception, motor) has a "
        "calibrated, ground-truth-checked confidence signal",
        effect="METACOGNITIVE cannot be claimed for the other six modules until each has both "
        "a self-reported confidence output and a resolvable outcome to check it against",
    )
    service.assess()
    return service


def assessment_report(
    service: HigherOrderCognitionService, self_model: SelfModelService | None = None
) -> dict[str, object]:
    """Summarize current stage attainment per module, plus the explicit
    not-yet list. This is the self-model surface: what the system can
    currently support a claim for, and what it plainly cannot yet.

    ``self_model``, if provided (from ``build_self_model()``), adds the
    claimed capabilities and recorded limitations to the report -- the
    same information ``SelfModelService.assess()`` produces, surfaced
    alongside the stage records rather than requiring a separate lookup.
    """
    by_module: dict[str, list[str]] = {}
    for record in service.stage_records.values():
        module = record.entered_because.split(":", 1)[0]
        by_module.setdefault(module, []).append(str(record.stage))
    report: dict[str, object] = {
        "stages_by_module": by_module,
        "not_yet_claimed": NOT_YET_CLAIMED,
        "blocked_claims": service.claim_boundary_report()["blocked"],
    }
    if self_model is not None:
        report["self_model_capabilities"] = [c.name for c in self_model.capabilities]
        report["self_model_limitations"] = [
            {"limitation": lim.limitation, "effect": lim.effect} for lim in self_model.limitations
        ]
    return report
