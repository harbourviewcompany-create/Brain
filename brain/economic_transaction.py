from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .economic_runtime import EconomicStore, FeeControl


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Mandate:
    transaction_id: UUID
    counterparty_entity_id: UUID
    scope: str
    exclusive: bool
    valid_until: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class IntroductionRecord:
    transaction_id: UUID
    introducing_party_id: UUID
    introduced_party_ids: list[UUID]
    evidence_ref: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class FeeAgreement:
    transaction_id: UUID
    payer_entity_id: UUID
    fee_model: str
    fee_value: float
    currency: str
    signed: bool
    jurisdiction: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ReferralAgreement:
    transaction_id: UUID
    referrer_entity_id: UUID
    payer_entity_id: UUID
    fee_value: float
    currency: str
    signed: bool
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ExclusivityRecord:
    transaction_id: UUID
    granting_entity_id: UUID
    scope: str
    valid_until: datetime
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class OriginationEvidence:
    transaction_id: UUID
    source_ref: str
    evidence_hash: str
    captured_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class DealRoom:
    transaction_id: UUID
    document_refs: list[str] = field(default_factory=list)
    participant_entity_ids: list[UUID] = field(default_factory=list)
    status: str = "open"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class TransactionControlService:
    """Persist transaction-control artifacts and derive the runtime fee-control gate."""

    def __init__(self, store: EconomicStore) -> None:
        self.store = store

    def save_mandate(self, mandate: Mandate) -> Mandate:
        self.store.put("mandate", mandate.id, mandate)
        return mandate

    def save_introduction(self, record: IntroductionRecord) -> IntroductionRecord:
        if not record.evidence_ref:
            raise ValueError("introduction_requires_evidence_ref")
        self.store.put("introduction_record", record.id, record)
        return record

    def save_fee_agreement(self, agreement: FeeAgreement) -> FeeAgreement:
        if agreement.fee_value < 0:
            raise ValueError("fee_value_cannot_be_negative")
        self.store.put("fee_agreement", agreement.id, agreement)
        return agreement

    def save_referral_agreement(self, agreement: ReferralAgreement) -> ReferralAgreement:
        self.store.put("referral_agreement", agreement.id, agreement)
        return agreement

    def save_exclusivity(self, record: ExclusivityRecord) -> ExclusivityRecord:
        self.store.put("exclusivity_record", record.id, record)
        return record

    def save_origination(self, evidence: OriginationEvidence) -> OriginationEvidence:
        if not evidence.evidence_hash:
            raise ValueError("origination_requires_hash")
        self.store.put("origination_evidence", evidence.id, evidence)
        return evidence

    def save_deal_room(self, room: DealRoom) -> DealRoom:
        self.store.put("deal_room", room.id, room)
        return room

    def derive_fee_control(
        self,
        transaction_id: UUID,
        *,
        jurisdiction_reviewed: bool,
    ) -> FeeControl:
        mandates = [m for m in self.store.list("mandate") if m.transaction_id == transaction_id]
        introductions = [
            i for i in self.store.list("introduction_record") if i.transaction_id == transaction_id
        ]
        fee_agreements = [
            f
            for f in self.store.list("fee_agreement")
            if f.transaction_id == transaction_id and f.signed
        ]
        exclusivities = [
            e for e in self.store.list("exclusivity_record") if e.transaction_id == transaction_id
        ]
        originations = [
            o for o in self.store.list("origination_evidence") if o.transaction_id == transaction_id
        ]
        control = FeeControl(
            transaction_id=transaction_id,
            mandate=bool(mandates),
            introduction_logged=bool(introductions),
            fee_agreement=bool(fee_agreements),
            exclusivity=bool(exclusivities),
            origination_evidence=bool(originations),
            jurisdiction_reviewed=jurisdiction_reviewed,
        )
        self.store.put("fee_control", control.id, control)
        return control
