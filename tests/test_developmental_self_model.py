import pytest

from brain.developmental.self_model import SelfModelService


def test_capability_claim_requires_evidence() -> None:
    service = SelfModelService()
    with pytest.raises(ValueError, match="capability_claim_requires"):
        service.claim_capability(
            name="full-brain-complete",
            confidence=1.0,
            evidence_refs=[],
            test_refs=[],
            acceptance_refs=[],
        )


def test_limitation_is_preserved() -> None:
    service = SelfModelService()
    limitation = service.record_limitation(
        limitation="no live connector may activate without source rights review",
        effect="blocks autonomous ingestion activation",
    )

    assert limitation.preserved is True
    assert service.limitations == [limitation]


def test_learning_debt_affects_priority() -> None:
    service = SelfModelService()
    service.add_learning_debt(
        area="calibration",
        severity=0.8,
        evidence_gap="insufficient outcome volume",
    )
    assessment = service.assess()

    assert assessment.learning_debt_priority == 0.8


def test_self_model_blocks_overclaiming() -> None:
    service = SelfModelService()
    service.record_limitation(
        limitation="developmental runtime is partial until acceptance reports exist",
        effect="blocks full completion claim",
    )
    service.claim_capability(
        name="prediction-error-runtime",
        confidence=0.8,
        evidence_refs=["reports/acceptance/AGENT-008-prediction-error-runtime.json"],
        test_refs=["tests/test_developmental_prediction_error.py"],
        acceptance_refs=["reports/acceptance/AGENT-008-prediction-error-runtime.json"],
    )
    assessment = service.assess()

    assert service.can_claim("prediction-error-runtime") is True
    assert service.can_claim("full-brain-complete") is False
    assert assessment.overclaim_blocked is True
