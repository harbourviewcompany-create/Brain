from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from brain.economic_transaction import (
    DealRoom,
    ExclusivityRecord,
    FeeAgreement,
    IntroductionRecord,
    Mandate,
    OriginationEvidence,
    ReferralAgreement,
    TransactionControlService,
)
from brain.economic_runtime import InMemoryEconomicStore


def test_transaction_control_derives_sufficient_fee_gate_from_records() -> None:
    store = InMemoryEconomicStore()
    service = TransactionControlService(store)
    transaction_id = uuid4()
    buyer_id = uuid4()
    seller_id = uuid4()

    service.save_mandate(
        Mandate(
            transaction_id=transaction_id,
            counterparty_entity_id=seller_id,
            scope="asset disposition",
            exclusive=False,
        )
    )
    service.save_introduction(
        IntroductionRecord(
            transaction_id=transaction_id,
            introducing_party_id=uuid4(),
            introduced_party_ids=[buyer_id, seller_id],
            evidence_ref="audit:intro-001",
        )
    )
    service.save_fee_agreement(
        FeeAgreement(
            transaction_id=transaction_id,
            payer_entity_id=seller_id,
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
            source_ref="source:listing-001",
            evidence_hash="sha256:abc123",
        )
    )

    control = service.derive_fee_control(transaction_id, jurisdiction_reviewed=True)
    assert control.sufficient(fee_sensitive=True) is True
    assert control.introduction_logged is True
    assert control.origination_evidence is True
    assert control.fee_agreement is True


def test_unsigned_fee_agreement_does_not_satisfy_fee_control() -> None:
    store = InMemoryEconomicStore()
    service = TransactionControlService(store)
    transaction_id = uuid4()
    payer = uuid4()
    service.save_introduction(
        IntroductionRecord(
            transaction_id=transaction_id,
            introducing_party_id=uuid4(),
            introduced_party_ids=[payer],
            evidence_ref="audit:intro-002",
        )
    )
    service.save_fee_agreement(
        FeeAgreement(
            transaction_id=transaction_id,
            payer_entity_id=payer,
            fee_model="success_fee",
            fee_value=5000,
            currency="USD",
            signed=False,
            jurisdiction="US-NY",
        )
    )
    service.save_origination(
        OriginationEvidence(
            transaction_id=transaction_id,
            source_ref="source:origin",
            evidence_hash="sha256:def456",
        )
    )
    control = service.derive_fee_control(transaction_id, jurisdiction_reviewed=True)
    assert control.fee_agreement is False
    assert control.sufficient(fee_sensitive=True) is False


def test_transaction_control_records_persist_independently() -> None:
    store = InMemoryEconomicStore()
    service = TransactionControlService(store)
    transaction_id = uuid4()
    party = uuid4()
    service.save_referral_agreement(
        ReferralAgreement(
            transaction_id=transaction_id,
            referrer_entity_id=uuid4(),
            payer_entity_id=party,
            fee_value=1000,
            currency="CAD",
            signed=True,
        )
    )
    service.save_exclusivity(
        ExclusivityRecord(
            transaction_id=transaction_id,
            granting_entity_id=party,
            scope="Ontario",
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
    )
    service.save_deal_room(
        DealRoom(
            transaction_id=transaction_id,
            document_refs=["doc:mandate", "doc:fee"],
            participant_entity_ids=[party],
        )
    )
    assert len(store.list("referral_agreement")) == 1
    assert len(store.list("exclusivity_record")) == 1
    assert len(store.list("deal_room")) == 1


def test_transaction_control_requires_evidence_for_intro_and_origination() -> None:
    service = TransactionControlService(InMemoryEconomicStore())
    with pytest.raises(ValueError, match="introduction_requires_evidence_ref"):
        service.save_introduction(
            IntroductionRecord(
                transaction_id=uuid4(),
                introducing_party_id=uuid4(),
                introduced_party_ids=[uuid4()],
                evidence_ref="",
            )
        )
    with pytest.raises(ValueError, match="origination_requires_hash"):
        service.save_origination(
            OriginationEvidence(
                transaction_id=uuid4(),
                source_ref="source:x",
                evidence_hash="",
            )
        )
