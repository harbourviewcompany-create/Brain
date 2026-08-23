from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from .economic_runtime import FeeControl, JurisdictionProfile, SourceRightsClass, SourceRightsProfile


class GateDisposition(StrEnum):
    GO = "GO"
    HOLD = "HOLD"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class GateDecision:
    disposition: GateDisposition
    reasons: list[str]
    required_evidence: list[str] = field(default_factory=list)
    required_approval: str | None = None
    audit_event: str = "gate.evaluated"
    id: UUID = field(default_factory=uuid4)

    @property
    def go_hold(self) -> str:
        return self.disposition.value


class SourceRightsGate:
    """MOD-013 source-rights gate for live connector activation."""

    SENSITIVE_CLASSES = {
        SourceRightsClass.SCRAPE_SENSITIVE,
        SourceRightsClass.PII_SENSITIVE,
        SourceRightsClass.REGULATED_DATA,
    }

    def evaluate(
        self,
        rights: SourceRightsProfile,
        jurisdiction: JurisdictionProfile,
        *,
        terms_reviewed: bool = False,
        permission_evidence: bool = False,
        license_evidence: bool = False,
    ) -> GateDecision:
        reasons: list[str] = []
        required: list[str] = []
        approval: str | None = None

        if rights.rights_class == SourceRightsClass.PROHIBITED:
            return GateDecision(
                disposition=GateDisposition.REJECT,
                reasons=["source_rights_profile_prohibited"],
                required_evidence=["replacement_source_or_explicit_rejection_record"],
                audit_event="source_rights.rejected",
            )

        if rights.rights_class in self.SENSITIVE_CLASSES:
            reasons.append("sensitive_source_requires_rights_review")
            required.append("source_rights_review")
            approval = "source_rights_officer"
        if rights.rights_class == SourceRightsClass.PUBLIC_TERMS_RESTRICTED and not terms_reviewed:
            reasons.append("public_terms_restricted_requires_terms_review")
            required.append("terms_review_record")
            approval = approval or "terms_review"
        if rights.rights_class == SourceRightsClass.PERMISSIONED and not permission_evidence:
            reasons.append("permissioned_source_requires_permission_evidence")
            required.append("permission_evidence")
            approval = approval or "permission_approval"
        if rights.rights_class == SourceRightsClass.PAID_LICENSED and not license_evidence:
            reasons.append("paid_source_requires_license_evidence")
            required.append("license_evidence")
            approval = approval or "license_approval"
        if not rights.permitted_collection:
            reasons.append("collection_not_permitted")
            required.append("collection_permission")
        if not rights.permitted_storage:
            reasons.append("storage_not_permitted")
            required.append("storage_permission")
        if not rights.permitted_commercial_use:
            reasons.append("commercial_use_not_permitted")
            required.append("commercial_use_permission")
        if jurisdiction.sanctions_review_required or jurisdiction.brokerage_review_required:
            reasons.append("jurisdiction_profile_requires_enhanced_review")
            required.append("jurisdiction_review")
            approval = approval or "jurisdiction_reviewer"
        if jurisdiction.data_restrictions:
            reasons.append("jurisdiction_data_restrictions_require_review")
            required.append("data_restriction_review")
            approval = approval or "data_rights_review"

        if reasons:
            return GateDecision(
                disposition=GateDisposition.HOLD,
                reasons=reasons,
                required_evidence=sorted(set(required)),
                required_approval=approval,
                audit_event="source_rights.hold",
            )

        return GateDecision(
            disposition=GateDisposition.GO,
            reasons=["source_rights_gate_clear"],
            audit_event="source_rights.go",
        )


class TransactionDisclosureGate:
    """MOD-012 fee-protection gate for consequential transaction disclosure."""

    def evaluate(
        self,
        control: FeeControl,
        jurisdiction: JurisdictionProfile,
        *,
        fee_sensitive: bool,
        approval_granted: bool,
    ) -> GateDecision:
        required: list[str] = []
        if fee_sensitive:
            if not control.mandate:
                required.append("mandate")
            if not control.introduction_logged:
                required.append("introduction_record")
            if not control.origination_evidence:
                required.append("origination_evidence")
            if not control.fee_agreement:
                required.append("fee_agreement")
        if not control.jurisdiction_reviewed:
            required.append("jurisdiction_review")
        if jurisdiction.brokerage_review_required or jurisdiction.sanctions_review_required:
            required.append("jurisdiction_enhanced_review")
        if not approval_granted:
            required.append("explicit_operator_approval")

        if required:
            return GateDecision(
                disposition=GateDisposition.HOLD,
                reasons=["transaction_disclosure_hold_missing_required_controls"],
                required_evidence=sorted(set(required)),
                required_approval="operator" if not approval_granted else "control_reviewer",
                audit_event="transaction.disclosure_hold",
            )

        return GateDecision(
            disposition=GateDisposition.GO,
            reasons=["transaction_disclosure_gate_clear"],
            audit_event="transaction.disclosure_go",
        )


def source_roi_attribution(
    *,
    attributed_net_profit: float,
    data_cost: float,
    attribution_confidence: float,
) -> float:
    """Return confidence-weighted source ROI with zero-cost protection."""

    return (attributed_net_profit * attribution_confidence) / max(data_cost, 1.0)
