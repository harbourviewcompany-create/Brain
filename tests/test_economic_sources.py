import pytest

from brain.economic_runtime import (
    InMemoryEconomicStore,
    JurisdictionProfile,
    SourcePlaneType,
    SourceRightsClass,
    SourceRightsProfile,
)
from brain.economic_sources import SourceMeshService


def test_source_candidate_requires_discovery_evidence() -> None:
    service = SourceMeshService(InMemoryEconomicStore())
    with pytest.raises(ValueError, match="discovery_evidence"):
        service.propose_source(
            source_key="registry-x",
            plane=SourcePlaneType.CORPORATE,
            jurisdiction="CA",
            discovery_evidence_refs=[],
            proposed_refresh_seconds=86400,
            rationale="corporate registry",
        )


def test_source_candidate_reviews_into_rights_linked_plane() -> None:
    store = InMemoryEconomicStore()
    service = SourceMeshService(store)
    jurisdiction = service.register_jurisdiction(
        JurisdictionProfile(code="CA-ON", currency="CAD", languages=["en", "fr"])
    )
    assert jurisdiction.currency == "CAD"
    candidate = service.propose_source(
        source_key="ontario-registry",
        plane=SourcePlaneType.CORPORATE,
        jurisdiction="CA-ON",
        discovery_evidence_refs=["source:government-directory"],
        proposed_refresh_seconds=86400,
        rationale="official corporate registry",
    )
    rights = SourceRightsProfile(
        source_key="ontario-registry",
        rights_class=SourceRightsClass.PUBLIC_SAFE,
        jurisdiction="CA-ON",
        permitted_collection=True,
        permitted_storage=True,
        permitted_commercial_use=True,
    )
    store.put("source_rights", rights.id, rights)
    source = service.review_candidate(candidate, rights=rights, reliability=0.95)
    assert source.rights_profile_id == rights.id
    assert source.status == "reviewed"


def test_recursive_source_discovery_is_proposal_not_auto_activation() -> None:
    store = InMemoryEconomicStore()
    service = SourceMeshService(store)
    candidate = service.propose_source(
        source_key="new-regulator",
        plane=SourcePlaneType.REGULATORY,
        jurisdiction="DE",
        discovery_evidence_refs=["filing:subsidiary-regulator-reference"],
        proposed_refresh_seconds=21600,
        rationale="filing disclosed relevant regulator",
    )
    proposal = service.propose_discovered_source(
        parent_source_key="filing-feed",
        candidate=candidate,
        discovered_relation="mentions_regulator",
        evidence_ref="filing:123#section-7",
    )
    assert proposal.candidate_id == candidate.id
    assert candidate.status == "candidate"
    assert store.list("source_plane") == []


def test_source_economics_updates_roi_and_promotion_gate() -> None:
    store = InMemoryEconomicStore()
    service = SourceMeshService(store)
    candidate = service.propose_source(
        source_key="market-feed",
        plane=SourcePlaneType.MARKETPLACE,
        jurisdiction="US",
        discovery_evidence_refs=["manual-source-audit"],
        proposed_refresh_seconds=3600,
        rationale="asset marketplace",
    )
    rights = SourceRightsProfile(
        source_key="market-feed",
        rights_class=SourceRightsClass.PUBLIC_SAFE,
        jurisdiction="US",
        permitted_collection=True,
        permitted_storage=True,
        permitted_commercial_use=True,
    )
    store.put("source_rights", rights.id, rights)
    source = service.review_candidate(candidate, rights=rights, reliability=0.8, estimated_cost=100)
    economics = service.record_economics(
        "market-feed",
        observations=100,
        signals=20,
        qualified_opportunities=4,
        transactions=1,
        gross_revenue=10000,
        net_profit=7000,
        api_data_cost=500,
        operator_hours=5,
        false_positives=4,
    )
    assert economics.direct_roi == 14
    assert service.promotion_gate(economics) == "GO"
    updated_source = store.get("source_plane", source.id)
    assert updated_source.attributed_net_profit == 7000
    assert updated_source.opportunity_yield == 0.04


def test_noisy_unproven_source_is_hold() -> None:
    service = SourceMeshService(InMemoryEconomicStore())
    economics = service.record_economics(
        "noisy",
        observations=20,
        signals=10,
        qualified_opportunities=0,
        false_positives=9,
    )
    assert service.promotion_gate(economics) == "HOLD"
