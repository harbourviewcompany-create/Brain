from uuid import uuid4

from brain.economic_hard_gates import (
    GateDisposition,
    SourceRightsGate,
    TransactionDisclosureGate,
    source_roi_attribution,
)
from brain.economic_runtime import (
    InMemoryEconomicStore,
    JurisdictionProfile,
    SourceRightsClass,
    SourceRightsProfile,
)
from brain.economic_transaction import (
    FeeAgreement,
    IntroductionRecord,
    Mandate,
    OriginationEvidence,
    TransactionControlService,
)


def test_prohibited_source_rejection() -> None:
    gate = SourceRightsGate()
    rights = SourceRightsProfile(
        source_key="forbidden-dataset",
        rights_class=SourceRightsClass.PROHIBITED,
        jurisdiction="US",
        permitted_collection=False,
        permitted_storage=False,
        permitted_commercial_use=False,
    )
    jurisdiction = JurisdictionProfile(code="US", currency="USD", languages=["en"])

    decision = gate.evaluate(rights, jurisdiction)

    assert decision.disposition == GateDisposition.REJECT
    assert "source_rights_profile_prohibited" in decision.reasons


def test_sensitive_source_hold() -> None:
    gate = SourceRightsGate()
    rights = SourceRightsProfile(
        source_key="candidate-pii-feed",
        rights_class=SourceRightsClass.PII_SENSITIVE,
        jurisdiction="CA-ON",
        permitted_collection=True,
        permitted_storage=True,
        permitted_commercial_use=False,
    )
    jurisdiction = JurisdictionProfile(
        code="CA-ON",
        currency="CAD",
        languages=["en", "fr"],
        data_restrictions=["PII"],
    )

    decision = gate.evaluate(rights, jurisdiction)

    assert decision.disposition == GateDisposition.HOLD
    assert "source_rights_review" in decision.required_evidence
    assert "commercial_use_permission" in decision.required_evidence


def test_jurisdiction_classification_requires_review() -> None:
    gate = SourceRightsGate()
    rights = SourceRightsProfile(
        source_key="brokerage-sensitive-feed",
        rights_class=SourceRightsClass.PUBLIC_SAFE,
        jurisdiction="US-NY",
        permitted_collection=True,
        permitted_storage=True,
        permitted_commercial_use=True,
    )
    jurisdiction = JurisdictionProfile(
        code="US-NY",
        currency="USD",
        languages=["en"],
        brokerage_review_required=True,
    )

    decision = gate.evaluate(rights, jurisdiction)

    assert decision.disposition == GateDisposition.HOLD
    assert "jurisdiction_review" in decision.required_evidence


def test_unprotected_transaction_disclosure_hold() -> None:
    service = TransactionControlService(InMemoryEconomicStore())
    transaction_id = uuid4()
    control = service.derive_fee_control(transaction_id, jurisdiction_reviewed=False)
    jurisdiction = JurisdictionProfile(code="CA-ON", currency="CAD", languages=["en"])

    decision = TransactionDisclosureGate().evaluate(
        control,
        jurisdiction,
        fee_sensitive=True,
        approval_granted=True,
    )

    assert decision.disposition == GateDisposition.HOLD
    assert "fee_agreement" in decision.required_evidence
    assert "origination_evidence" in decision.required_evidence


def test_approval_bypass_blocked_until_explicit_approval() -> None:
    store = InMemoryEconomicStore()
    service = TransactionControlService(store)
    transaction_id = uuid4()
    payer = uuid4()
    buyer = uuid4()
    service.save_mandate(
        Mandate(
            transaction_id=transaction_id,
            counterparty_entity_id=payer,
            scope="asset disposition",
            exclusive=False,
        )
    )
    service.save_introduction(
        IntroductionRecord(
            transaction_id=transaction_id,
            introducing_party_id=uuid4(),
            introduced_party_ids=[buyer, payer],
            evidence_ref="audit:intro-001",
        )
    )
    service.save_fee_agreement(
        FeeAgreement(
            transaction_id=transaction_id,
            payer_entity_id=payer,
            fee_model="success_fee",
            fee_value=0.05,
            currency="CAD",
            signed=True,
            jurisdiction="CA-ON",
        )
    )
    service.save_origination(
        OriginationEvidence(
            transaction_id=transaction_id,
            source_ref="source:registry",
            evidence_hash="sha256:abc123",
        )
    )
    control = service.derive_fee_control(transaction_id, jurisdiction_reviewed=True)
    jurisdiction = JurisdictionProfile(code="CA-ON", currency="CAD", languages=["en"])

    blocked = TransactionDisclosureGate().evaluate(
        control,
        jurisdiction,
        fee_sensitive=True,
        approval_granted=False,
    )
    approved = TransactionDisclosureGate().evaluate(
        control,
        jurisdiction,
        fee_sensitive=True,
        approval_granted=True,
    )

    assert blocked.disposition == GateDisposition.HOLD
    assert "explicit_operator_approval" in blocked.required_evidence
    assert approved.disposition == GateDisposition.GO


def test_source_roi_attribution() -> None:
    assert source_roi_attribution(
        attributed_net_profit=7000,
        data_cost=500,
        attribution_confidence=0.8,
    ) == 11.2
