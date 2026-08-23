import pytest

from brain.developmental.theory_registry import TheoryRegistryService


def test_unknown_is_not_deleted() -> None:
    service = TheoryRegistryService()
    unknown = service.register_unknown(
        question="why did this source predict conversion incorrectly?",
        context_refs=["trace:prediction-error"],
    )

    assert unknown.status == "unknown"
    assert service.unknowns[unknown.id] == unknown


def test_theory_competition_preserves_alternatives() -> None:
    service = TheoryRegistryService()
    unknown = service.register_unknown(
        question="what mechanism drove buyer response?",
        context_refs=["outcome:reply"],
    )
    timing = service.add_theory(
        unknown,
        name="timing-advantage",
        explanation="response came from fast timing",
        speculative=True,
        evidence_refs=["evidence:timestamp"],
    )
    trust = service.add_theory(
        unknown,
        name="trust-channel",
        explanation="response came from trusted path",
        speculative=True,
        evidence_refs=["evidence:relationship"],
    )
    competition = service.create_competition(unknown, [timing.id, trust.id])

    assert competition.preserved_alternatives is True
    assert competition.theory_ids == [timing.id, trust.id]


def test_speculative_status_is_explicit() -> None:
    service = TheoryRegistryService()
    unknown = service.register_unknown(question="unexplained reward spike", context_refs=["reward:spike"])
    theory = service.add_theory(
        unknown,
        name="hidden-source-quality",
        explanation="source may contain an unseen quality signal",
        speculative=True,
        evidence_refs=[],
    )

    assert theory.status == "speculative"


def test_theory_promotion_requires_evidence() -> None:
    service = TheoryRegistryService()
    unknown = service.register_unknown(question="unknown", context_refs=["trace:x"])
    theory = service.add_theory(
        unknown,
        name="candidate",
        explanation="candidate explanation",
        speculative=True,
        evidence_refs=["evidence:one"],
    )
    with pytest.raises(ValueError, match="theory_promotion_requires_evidence"):
        service.promote_theory(theory, evidence_refs=["evidence:one"])

    promoted = service.promote_theory(theory, evidence_refs=["evidence:two", "evidence:three"])
    assert promoted.status == "supported"
    assert "evidence:three" in promoted.evidence_refs
