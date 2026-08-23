from datetime import timedelta
from uuid import uuid4

import pytest

from brain.economic_atomic_lifecycles import (
    AtomicEconomicReplayService,
    AtomicTransitionLedger,
    CanonicalCapitalLifecycleService,
    CanonicalCompoundingLifecycleService,
    CanonicalOpportunityLifecycleService,
    CanonicalPressureLifecycleService,
    CounterpartyLifecycleService,
    MovementObservation,
    ProvenancedMovementDetector,
    SourceActivationContract,
    SourceActivationService,
    disposition_contracts,
    jurisdiction_complete,
    money_path_expired,
    utcnow,
)
from brain.economic_atomic_services import (
    AffordanceGenerationService,
    AsymmetryDetectionService,
    AttributionDownstreamGateService,
    AttributionLifecycleService,
    BusinessModelMutationService,
    BuyerMatchService,
    CommercialSkepticService,
    CounterpartyProfileRecord,
    CounterpartyProfileService,
    EconomicOpportunityScoringService,
    FeeProtectionDecision,
    FeeProtectionService,
    GeneratedMoneyPath,
    InternationalJurisdictionProfile,
    LiquidityGraphService,
    MandateRecord,
    MandateService,
    MarketplaceEmergenceService,
    MoneyPathGenerationService,
    MoneyPathLifecycleService,
    PortfolioAllocationService,
    PressureInferenceService,
    ProductizationService,
    SellerMatchService,
    SourceDiscoveryService,
    SourceEconomicsRecord,
    SourceEconomicsService,
    SourceLifecycleService,
    SourcePlaneRegistryService,
    SourceReliabilityService,
    SourceRightsService,
    SourceROIService,
    TransactionStateService,
)
from brain.economic_conformance import (
    CausalAttributionChain,
    CollectionMethod,
    CompoundingEmergenceService,
    ConformanceStore,
    ConformanceVerdict,
    CounterpartyInteraction,
    LifecycleState,
    LiquidityPreference,
    OperatorDisposition,
    OpportunityLifecycleService,
    SourceActivationPolicy,
    SourceRightsClass,
)


def evidence() -> list[str]:
    return ["fixture:atomic", "source:trace"]


def test_mod008_named_services_infer_pressure_and_support_contradiction_reverification() -> None:
    asymmetry = AsymmetryDetectionService().detect(
        asymmetry_type="distress",
        indicators={"payment_delay": 0.8, "inventory": 0.6},
        evidence_refs=evidence(),
    )
    assert 0 < asymmetry.magnitude <= 1
    pressure = PressureInferenceService().infer(
        pressure_type="liquidity_pressure",
        signal_strengths=[0.9, 0.7],
        evidence_refs=evidence(),
        direction="worsening",
    )
    assert 0 < pressure.confidence <= 1

    ledger = AtomicTransitionLedger()
    lifecycle = CanonicalPressureLifecycleService()
    pressure_id = uuid4()
    lifecycle.transition(
        ledger,
        pressure_id=pressure_id,
        from_state="hypothesized",
        to_state="supported",
        evidence_refs=evidence(),
        trigger="corroborated",
    )
    lifecycle.transition(
        ledger,
        pressure_id=pressure_id,
        from_state="supported",
        to_state="invalidated",
        evidence_refs=evidence(),
        trigger="contradicted",
    )
    lifecycle.transition(
        ledger,
        pressure_id=pressure_id,
        from_state="invalidated",
        to_state="hypothesized",
        evidence_refs=evidence(),
        trigger="reverification",
    )
    with pytest.raises(ValueError, match="time_valid"):
        lifecycle.transition(
            ledger,
            pressure_id=pressure_id,
            from_state="supported",
            to_state="active",
            evidence_refs=evidence(),
            valid_until=utcnow() - timedelta(seconds=1),
            trigger="expired",
        )


def test_mod009_affordance_money_path_services_cover_grammar_rank_expiry_and_nonmonetizable() -> None:
    verbs = AffordanceGenerationService().generate(
        pressure_tags=["capacity_gap", "distress", "regulatory_change", "ownership_change"],
        evidence_refs=evidence(),
    )
    assert {"build", "finance", "restructure", "advise", "acquire", "exit"} <= set(verbs)

    service = MoneyPathGenerationService()
    monetizable = service.generate(
        verb="broker",
        payer_id=uuid4(),
        payment_mechanism="success_fee",
        expected_net_value=5000,
        required_capital=200,
        risk=0.2,
        repeatability=0.7,
        compounding_value=0.6,
        evidence_refs=evidence(),
    )
    nonmonetizable = service.generate(
        verb="advise",
        payer_id=None,
        payment_mechanism=None,
        expected_net_value=0,
        required_capital=0,
        risk=0.1,
        repeatability=0.1,
        compounding_value=0.1,
        evidence_refs=evidence(),
    )
    assert nonmonetizable.disposition == OperatorDisposition.NON_MONETIZABLE
    ranking = MoneyPathLifecycleService().rank([monetizable, nonmonetizable])
    assert ranking.best_overall == monetizable.id
    monetizable.valid_until = utcnow() - timedelta(seconds=1)
    assert money_path_expired(monetizable)


def test_mod010_persistent_liquidity_graph_role_matching_weighting_and_stale_transition() -> None:
    store = ConformanceStore()
    party_id = uuid4()
    profile = CounterpartyProfileRecord(party_id, 0.9, 0.8, 0.7, evidence())
    CounterpartyProfileService().persist(store, profile)
    prefs = [LiquidityPreference(party_id, "budget", "low_capex", 0.9, evidence())]
    interactions = [
        CounterpartyInteraction(party_id, "email", "response", 4, evidence(), occurred_at=utcnow() - timedelta(days=120))
    ]
    graph = LiquidityGraphService().build_and_persist(
        store,
        counterparty_id=party_id,
        preferences=prefs,
        interactions=interactions,
        role_evidence={"buyer": ["source:a", "source:b"]},
    )
    assert store.list("liquidity_preference") == prefs
    assert store.list("counterparty_interaction") == interactions
    assert graph.nodes[0].verified_roles == ["buyer"]
    buyer_score = BuyerMatchService().score(profile, graph.nodes[0].response_history_weight)
    seller_score = SellerMatchService().score(profile, graph.nodes[0].response_history_weight)
    assert buyer_score == seller_score
    ledger = AtomicTransitionLedger()
    transition = CounterpartyLifecycleService().stale_transition(
        ledger,
        counterparty_id=party_id,
        current_state="active",
        last_interaction_at=utcnow() - timedelta(days=120),
        stale_after_days=90,
        evidence_refs=evidence(),
    )
    assert transition is not None and transition.to_state == "dormant"


def test_mod011_portfolio_scoring_skeptic_canonical_dispositions_and_time_expiry() -> None:
    score = EconomicOpportunityScoringService().score(
        expected_value=10000,
        probability=0.6,
        risk=0.2,
        required_effort=0.3,
    )
    assert score > 0
    assert CommercialSkepticService().disposition(
        payer_verified=False,
        payment_path_verified=False,
        expected_value=10000,
        evidence_refs=evidence(),
    ) == OperatorDisposition.NON_MONETIZABLE
    assert "build_as_asset" in disposition_contracts()

    ledger = AtomicTransitionLedger()
    lifecycle = CanonicalOpportunityLifecycleService()
    opportunity_id = uuid4()
    lifecycle.transition(ledger, opportunity_id=opportunity_id, from_state="detected", to_state="verifying", evidence_refs=evidence(), trigger="verify")
    lifecycle.transition(ledger, opportunity_id=opportunity_id, from_state="verifying", to_state="qualified", evidence_refs=evidence(), trigger="qualified")
    lifecycle.transition(ledger, opportunity_id=opportunity_id, from_state="qualified", to_state="build_as_asset", evidence_refs=evidence(), trigger="repeatable")
    expiring_id = uuid4()
    expired = lifecycle.expire_if_stale(
        ledger,
        opportunity_id=expiring_id,
        current_state="qualified",
        expires_at=utcnow() - timedelta(seconds=1),
        evidence_refs=evidence(),
    )
    assert expired is not None and expired.to_state == "expired"

    generated = OpportunityLifecycleService().disposition_to_state(
        opportunity_id=uuid4(),
        disposition=OperatorDisposition.WATCH,
        evidence_refs=evidence(),
        rationale="monitor",
    )
    portfolio = PortfolioAllocationService().persist(store := ConformanceStore(), lifecycles=[generated], attention_limit=1)
    assert store.list("opportunity_portfolio") == [portfolio]


def test_mod012_named_transaction_fee_and_mandate_boundaries() -> None:
    tx_service = TransactionStateService()
    tx_id = uuid4()
    assert tx_service.close(tx_id, 100, 80, evidence()).outcome == LifecycleState.CLOSED
    assert tx_service.loss(tx_id, evidence()).outcome == LifecycleState.LOST
    assert tx_service.abandon(tx_id, evidence()).outcome == LifecycleState.ABANDONED
    assert FeeProtectionService().verdict(FeeProtectionDecision(True, True, True, evidence())) == ConformanceVerdict.GO
    store = ConformanceStore()
    mandate = MandateRecord(uuid4(), "exclusive introduction", True, "CA-ON", evidence())
    MandateService().persist(store, mandate)
    assert store.list("mandate_record") == [mandate]


def test_mod013_named_source_services_reliability_lifecycle_activation_and_global_jurisdiction() -> None:
    store = ConformanceStore()
    registry_id = SourcePlaneRegistryService().persist(store, source_key="registry", payload={"plane": "corporate"}, evidence_refs=evidence())
    assert registry_id
    assert SourceDiscoveryService().propose(store, candidate={"url": "candidate"}, evidence_refs=evidence())
    record = SourceEconomicsRecord("registry", 100, 9, 1, 500, evidence())
    assert SourceEconomicsService().evaluate(record) == ConformanceVerdict.GO
    assert SourceROIService().score(record) == 4.0
    reliability = SourceReliabilityService().calibrate(confirmations=9, contradictions=1, freshness=0.8, provenance_quality=0.9)
    assert 0.0 < reliability <= 1.0
    assert SourceLifecycleService().transition(from_state="candidate", to_state="reviewed", evidence_refs=evidence()) == "reviewed"

    policy = SourceActivationPolicy("registry", SourceRightsClass.PUBLIC_SAFE, CollectionMethod.PUBLIC_API, evidence(), "CA-ON", True, True, True)
    assert SourceRightsService().verdict(policy) == ConformanceVerdict.GO
    contract = SourceActivationContract(policy=policy, refresh_policy="daily", provenance_refs=evidence())
    assert SourceActivationService().verdict(contract) == ConformanceVerdict.GO

    jurisdiction = InternationalJurisdictionProfile(
        jurisdiction="CA-ON",
        currency="CAD",
        languages=["en", "fr"],
        registries=["Ontario Business Registry"],
        regulators=["OSC"],
        licensing_regimes=["brokerage review"],
        procurement_systems=["Ontario Tenders Portal"],
        courts=["Ontario Superior Court"],
        trade_rules=["CUSMA"],
        entity_types=["corporation", "partnership"],
        import_export_rules=["CBSA"],
        business_norms=["written mandate"],
        source_reliability_notes=["official registry preferred"],
        evidence_refs=evidence(),
    )
    assert jurisdiction_complete(jurisdiction)
    movement: MovementObservation = ProvenancedMovementDetector().detect(
        entity_id=uuid4(), observation_id=uuid4(), source_key="registry", movement_type="headcount", before=10, after=20, evidence_refs=evidence()
    )
    assert movement.source_key == "registry" and movement.direction == "up"


def test_mod014_downstream_attribution_gates_and_canonical_capital_lifecycle() -> None:
    chain = CausalAttributionChain(
        uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), "source:registry", uuid4(), uuid4(), 0.85, evidence()
    )
    gate = AttributionDownstreamGateService()
    for operation in sorted(gate.operations):
        assert gate.verdict(operation=operation, chain=chain) == ConformanceVerdict.GO
    low = CausalAttributionChain(
        uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), "source:registry", uuid4(), uuid4(), 0.2, evidence()
    )
    assert gate.verdict(operation="capital_reallocation", chain=low) == ConformanceVerdict.HOLD
    assert AttributionLifecycleService().transition(from_state="provisional", to_state="supported", evidence_refs=evidence()) == "supported"

    ledger = AtomicTransitionLedger()
    capital = CanonicalCapitalLifecycleService()
    allocation_id = uuid4()
    capital.transition(ledger, allocation_id=allocation_id, from_state="proposed", to_state="operator_approved", evidence_refs=evidence(), trigger="approval")
    capital.transition(ledger, allocation_id=allocation_id, from_state="operator_approved", to_state="reserved", evidence_refs=evidence(), trigger="reserve")
    capital.transition(ledger, allocation_id=allocation_id, from_state="reserved", to_state="deployed", evidence_refs=evidence(), trigger="deploy")
    capital.transition(ledger, allocation_id=allocation_id, from_state="deployed", to_state="reconciled", evidence_refs=evidence(), trigger="reconcile")
    assert [item.to_state for item in ledger.transitions[-4:]] == ["operator_approved", "reserved", "deployed", "reconciled"]


def test_mod015_named_product_marketplace_business_model_services_resource_gate_and_canonical_progression() -> None:
    pattern = CompoundingEmergenceService().detect_repeated_pattern(
        pattern_key="buyer-matching",
        transaction_ids=[uuid4(), uuid4()],
        payer_ids=[uuid4()],
        evidence_refs=evidence(),
    )
    for service in (ProductizationService(), MarketplaceEmergenceService(), BusinessModelMutationService()):
        candidate = service.build_candidate(candidate_type="product", pattern=pattern, resource_estimate=1000)
        assert candidate.resource_estimate == 1000
    with pytest.raises(ValueError, match="resource_estimate"):
        ProductizationService().build_candidate(candidate_type="product", pattern=pattern, resource_estimate=0)

    ledger = AtomicTransitionLedger()
    lifecycle = CanonicalCompoundingLifecycleService()
    object_id = uuid4()
    lifecycle.transition(ledger, object_id=object_id, from_state="observed", to_state="hypothesized", evidence_refs=evidence(), resource_estimate=None, trigger="pattern")
    lifecycle.transition(ledger, object_id=object_id, from_state="hypothesized", to_state="validated", evidence_refs=evidence(), resource_estimate=None, trigger="validated")
    lifecycle.transition(ledger, object_id=object_id, from_state="validated", to_state="build_candidate", evidence_refs=evidence(), resource_estimate=1000, trigger="candidate")
    lifecycle.transition(ledger, object_id=object_id, from_state="build_candidate", to_state="approved", evidence_refs=evidence(), resource_estimate=1000, trigger="approval")
    lifecycle.transition(ledger, object_id=object_id, from_state="approved", to_state="operating", evidence_refs=evidence(), resource_estimate=1000, trigger="operate")
    assert ledger.transitions[-1].to_state == "operating"


def test_complete_fixture_universe_replays_deterministically_with_expected_go_hold_cases() -> None:
    scenarios = [
        "expansion", "distress", "supply_gap", "false_positive", "equipment", "hiring", "facility_permit", "regulatory_change", "fragmented_market",
        "active_buyer", "latent_buyer", "distressed_seller", "conflicting_role", "unreachable_decision_maker", "crowded_obvious", "inaccessible_payer", "zero_payment", "micro_cash", "strategic_mandate",
        "success_fee_intro", "exclusive_mandate", "regulated_brokerage", "public_registry", "paid_licensed", "scrape_sensitive", "pii_sensitive", "prohibited_source",
        "profitable_deal", "high_revenue_low_profit", "ambiguous_attribution", "multi_currency", "repeated_buyer_matching", "repeated_market_entry", "one_off_non_repeatable",
    ]
    results = AtomicEconomicReplayService().replay_all(scenarios)
    by_name = {result.scenario: result.verdict for result in results}
    assert by_name["expansion"] == ConformanceVerdict.GO
    assert by_name["false_positive"] == ConformanceVerdict.HOLD
    assert by_name["prohibited_source"] == ConformanceVerdict.HOLD
    assert by_name["one_off_non_repeatable"] == ConformanceVerdict.HOLD
