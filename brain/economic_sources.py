from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .economic_runtime import (
    EconomicStore,
    JurisdictionProfile,
    SourcePlane,
    SourcePlaneType,
    SourceRightsProfile,
)


@dataclass(slots=True)
class SourceCandidate:
    source_key: str
    plane: SourcePlaneType
    jurisdiction: str
    discovery_evidence_refs: list[str]
    proposed_refresh_seconds: int
    rationale: str
    status: str = "candidate"
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SourceEconomics:
    source_key: str
    observations: int = 0
    signals: int = 0
    qualified_opportunities: int = 0
    transactions: int = 0
    gross_revenue: float = 0.0
    net_profit: float = 0.0
    api_data_cost: float = 0.0
    operator_hours: float = 0.0
    false_positives: int = 0
    id: UUID = field(default_factory=uuid4)

    @property
    def direct_roi(self) -> float:
        return self.net_profit / max(self.api_data_cost, 1.0)

    @property
    def opportunity_yield(self) -> float:
        return self.qualified_opportunities / max(self.observations, 1)

    @property
    def false_positive_rate(self) -> float:
        return self.false_positives / max(self.signals, 1)


@dataclass(slots=True)
class SourceDiscoveryProposal:
    parent_source_key: str
    candidate_id: UUID
    discovered_relation: str
    evidence_ref: str
    id: UUID = field(default_factory=uuid4)


class SourceMeshService:
    """MOD-013 global source registry, discovery proposals, and economic feedback."""

    def __init__(self, store: EconomicStore) -> None:
        self.store = store

    def register_jurisdiction(self, profile: JurisdictionProfile) -> JurisdictionProfile:
        if not profile.code or not profile.currency:
            raise ValueError("jurisdiction_requires_code_and_currency")
        self.store.put("jurisdiction", profile.id, profile)
        return profile

    def propose_source(
        self,
        *,
        source_key: str,
        plane: SourcePlaneType,
        jurisdiction: str,
        discovery_evidence_refs: list[str],
        proposed_refresh_seconds: int,
        rationale: str,
    ) -> SourceCandidate:
        if not discovery_evidence_refs:
            raise ValueError("source_candidate_requires_discovery_evidence")
        if proposed_refresh_seconds <= 0:
            raise ValueError("source_refresh_must_be_positive")
        candidate = SourceCandidate(
            source_key=source_key,
            plane=plane,
            jurisdiction=jurisdiction,
            discovery_evidence_refs=discovery_evidence_refs,
            proposed_refresh_seconds=proposed_refresh_seconds,
            rationale=rationale,
        )
        self.store.put("source_candidate", candidate.id, candidate)
        return candidate

    def review_candidate(
        self,
        candidate: SourceCandidate,
        *,
        rights: SourceRightsProfile,
        reliability: float,
        estimated_cost: float = 0.0,
    ) -> SourcePlane:
        if candidate.source_key != rights.source_key:
            raise ValueError("source_candidate_rights_key_mismatch")
        if not 0.0 <= reliability <= 1.0:
            raise ValueError("source_reliability_out_of_range")
        candidate.status = "reviewed"
        self.store.put("source_candidate", candidate.id, candidate)
        source = SourcePlane(
            source_key=candidate.source_key,
            plane=candidate.plane,
            jurisdiction=candidate.jurisdiction,
            rights_profile_id=rights.id,
            refresh_seconds=candidate.proposed_refresh_seconds,
            reliability=reliability,
            estimated_cost=max(estimated_cost, 0.0),
            status="reviewed",
        )
        self.store.put("source_plane", source.id, source)
        return source

    def propose_discovered_source(
        self,
        *,
        parent_source_key: str,
        candidate: SourceCandidate,
        discovered_relation: str,
        evidence_ref: str,
    ) -> SourceDiscoveryProposal:
        if not evidence_ref:
            raise ValueError("source_discovery_requires_evidence")
        proposal = SourceDiscoveryProposal(
            parent_source_key=parent_source_key,
            candidate_id=candidate.id,
            discovered_relation=discovered_relation,
            evidence_ref=evidence_ref,
        )
        self.store.put("source_discovery_proposal", proposal.id, proposal)
        return proposal

    def record_economics(
        self,
        source_key: str,
        *,
        observations: int = 0,
        signals: int = 0,
        qualified_opportunities: int = 0,
        transactions: int = 0,
        gross_revenue: float = 0.0,
        net_profit: float = 0.0,
        api_data_cost: float = 0.0,
        operator_hours: float = 0.0,
        false_positives: int = 0,
    ) -> SourceEconomics:
        existing = next(
            (item for item in self.store.list("source_economics") if item.source_key == source_key),
            None,
        )
        if existing is None:
            existing = SourceEconomics(source_key=source_key)
        existing.observations += max(observations, 0)
        existing.signals += max(signals, 0)
        existing.qualified_opportunities += max(qualified_opportunities, 0)
        existing.transactions += max(transactions, 0)
        existing.gross_revenue += gross_revenue
        existing.net_profit += net_profit
        existing.api_data_cost += max(api_data_cost, 0.0)
        existing.operator_hours += max(operator_hours, 0.0)
        existing.false_positives += max(false_positives, 0)
        self.store.put("source_economics", existing.id, existing)
        for source in self.store.list("source_plane"):
            if source.source_key == source_key:
                source.signal_yield = existing.signals / max(existing.observations, 1)
                source.opportunity_yield = existing.opportunity_yield
                source.attributed_net_profit = existing.net_profit
                source.estimated_cost = existing.api_data_cost
                self.store.put("source_plane", source.id, source)
        return existing

    def promotion_gate(
        self,
        economics: SourceEconomics,
        *,
        minimum_observations: int = 10,
        maximum_false_positive_rate: float = 0.5,
    ) -> str:
        if economics.observations < minimum_observations:
            return "HOLD"
        if economics.false_positive_rate > maximum_false_positive_rate:
            return "HOLD"
        if economics.qualified_opportunities <= 0:
            return "HOLD"
        return "GO"
