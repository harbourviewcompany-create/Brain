from __future__ import annotations

import pytest

from brain.developmental.cognitive_extension_curriculum import (
    NOT_YET_CLAIMED,
    assessment_report,
    build_curriculum,
)
from brain.developmental.higher_order_cognition import (
    DevelopmentalStage,
    DevelopmentalStageRecord,
    HigherOrderCognitionService,
)


def test_build_curriculum_produces_stage_records_for_every_evidence_entry():
    service = build_curriculum()
    stages_seen = {record.stage for record in service.stage_records.values()}
    assert DevelopmentalStage.REFLEX in stages_seen
    assert DevelopmentalStage.PERCEPTUAL in stages_seen
    assert DevelopmentalStage.ASSOCIATIVE in stages_seen
    assert DevelopmentalStage.PREDICTIVE in stages_seen
    assert DevelopmentalStage.STRATEGIC in stages_seen
    # never claimed without wiring a real capability first
    assert DevelopmentalStage.METACOGNITIVE not in stages_seen
    assert DevelopmentalStage.SELF_REPAIRING not in stages_seen
    assert DevelopmentalStage.CONSOLIDATED not in stages_seen


def test_all_seven_modules_reach_reflex_stage():
    service = build_curriculum()
    reflex_modules = {
        r.entered_because.split(":", 1)[0]
        for r in service.stage_records.values()
        if r.stage == DevelopmentalStage.REFLEX
    }
    assert reflex_modules == {
        "brain/affect.py", "brain/executive.py", "brain/circadian.py",
        "brain/theory_of_mind.py", "brain/hedonic.py", "brain/perception.py",
        "brain/motor.py",
    }


def test_only_perception_reaches_perceptual_stage():
    service = build_curriculum()
    perceptual_modules = {
        r.entered_because.split(":", 1)[0]
        for r in service.stage_records.values()
        if r.stage == DevelopmentalStage.PERCEPTUAL
    }
    assert perceptual_modules == {"brain/perception.py"}


def test_only_executive_reaches_strategic_stage():
    service = build_curriculum()
    strategic_modules = {
        r.entered_because.split(":", 1)[0]
        for r in service.stage_records.values()
        if r.stage == DevelopmentalStage.STRATEGIC
    }
    assert strategic_modules == {"brain/executive.py"}


def test_every_stage_record_carries_evidence_and_blocked_claims():
    service = build_curriculum()
    for record in service.stage_records.values():
        assert record.evidence_refs
        assert "consciousness_claim" in record.blocked_claims
        assert "neuroscience_equivalence_claim" in record.blocked_claims


def test_advanced_stage_still_requires_capability_evidence_even_via_curriculum_service():
    """The curriculum module doesn't bypass HigherOrderCognitionService's
    own enforcement -- attempting METACOGNITIVE without
    capabilities_unlocked still raises, proving nothing here weakens the
    underlying gate."""
    service = HigherOrderCognitionService()
    with pytest.raises(ValueError, match="advanced_stage_requires_capability_evidence"):
        service.enter_developmental_stage(
            DevelopmentalStageRecord(
                stage=DevelopmentalStage.METACOGNITIVE,
                entered_because="brain/affect.py: unsupported premature claim",
                evidence_refs=["tests/test_affect.py"],
                capabilities_unlocked=[],
            )
        )


def test_assessment_report_lists_not_yet_claimed_items():
    service = build_curriculum()
    report = assessment_report(service)
    assert report["not_yet_claimed"] == NOT_YET_CLAIMED
    assert "consciousness_claim" in report["blocked_claims"]
    assert "brain/affect.py" in report["stages_by_module"]
    assert "reflex" in report["stages_by_module"]["brain/affect.py"]


def test_not_yet_claimed_explicitly_names_all_three_most_advanced_stages():
    joined = " ".join(NOT_YET_CLAIMED)
    assert "METACOGNITIVE" in joined
    assert "SELF_REPAIRING" in joined
    assert "CONSOLIDATED" in joined
