from datetime import timedelta
from uuid import uuid4

import pytest

from brain.economic_conformance import (
    AttributionPromotionService,
    CapitalLifecycleService,
    CausalAttributionChain,
    CollectionMethod,
    CompoundingEmergenceService,
    ConformanceStore,
    ConformanceVerdict,
    CounterpartyInteraction,
    CounterpartyLiquidityService,
    DeterministicFixtureFamily,
    EconomicStateMachineService,
    FixtureUniverseValidator,
    LifecycleState,
    LiquidityPreference,
    MoneyPathComparison,
    MoneyPathComparisonService,
    MovementChangeDetector,
    OperatorDisposition,
    OperatorSurfaceConformanceService,
    OperatorSurfaceRequirement,
    OpportunityLifecycleService,
    ProfitEvent,
    ProfitNormalizationService,
    SourceActivationPolicy,
    SourcePolicyService,
    SourceRightsClass,
    TransactionLifecycleService,
    summarize_mod_008_015_verdict,
    utcnow,
)


def evidence() -> list[str]:
    return ["fixture:mod-008-015-complete", "audit:atomic-repair"]


def test_pressure_activation_requires_evidence_and_time_validity() -> None:
    store = ConformanceStore()
    machine = EconomicStateMachineService()
    pressure_id = uuid4()
    with pytest.raises(ValueError, match="transition_requires_evidence"):
        machine.transition(
            store,
            machine="pressure",
            object_id=pressure_id,
            from_state=LifecycleState.SUPPORTED,
            to_state=LifecycleState.ACTIVE,
            trigger="invalid",
            evidence_refs=[],
            valid_until=utcnow() + timedelta(days=1),
        )
    with pytest.raises(ValueError, match="time_valid"):
        machine.transition(
            store,
            machine="pressure",
            object_id=pressure_id,
            from_state=LifecycleState.SUPPORTED,
            to_state=LifecycleState.ACTIVE,
            trigger="expired_evidence",
            evidence_refs=evidence(),
            valid_until=utcnow() - timedelta(days=1),
        )
    event = machine.transition(
        store,
        machine="pressure",
        object_id=pressure_id,
        from_state=LifecycleState.SUPPORTED,
        to_state=LifecycleState.ACTIVE,
        trigger="evidence_threshold_met",
        evidence_refs=evidence(),
        valid_until=utcnow() + timedelta(days=10),
        formula_run_ref="pressure_activation_v1",
    )
    assert event.to_state == "active"
    assert store.audit_log == [event]


def test_money_paths_are_ranked_across_required_dimensions() -> None:
    fast = MoneyPathComparison(uuid4(), 4000, 2, 500, 0.3, 0.4, 0.2, evidence())
    valuable = MoneyPathComparison(uuid4(), 25000, 30, 5000, 0.4, 0.5, 0.6, evidence())
    repeatable = MoneyPathComparison(uuid4(), 8000, 7, 800, 0.2, 0.95, 0.9, evidence())
    ranking = MoneyPathComparisonService().rank([fast, valuable, repeatable])
    assert ranking.fastest == fast.money_path_id
    assert ranking.highest_value == valuable.money_path_id
    assert ranking.lowest_capital == fast.money_path_id
    assert ranking.lowest_risk == repeatable.money_path_id
    assert ranking.most_repeatable == repeatable.money_path_id
    assert ranking.most_compounding == repeatable.money_path_id
    assert ranking.formula_run_ref == "money_path_atomic_rank_v1"


def test_counterparty_liquidity_graph_tracks_preferences_interactions_and_staleness() -> None:
    party_id = uuid4()
    preferences = [LiquidityPreference(party_id, "budget", "low_capex", 0.9, evidence())]
    interactions = [
        CounterpartyInteraction(
            party_id,
            "email",
            "response",
            4,
            evidence(),
            occurred_at=utcnow() - timedelta(days=5),
        ),
        CounterpartyInteraction(
            party_id,
            "phone",
            "no_response",
            None,
            evidence(),
            occurred_at=utcnow() - timedelta(days=4),
        ),
    ]
    node = CounterpartyLiquidityService().build_node(
        counterparty_id=party_id,
        preferences=preferences,
        interactions=interactions,
        role_evidence={"buyer": ["evidence:a", "evidence:b"], "operator": ["evidence:c"]},
    )
    assert "buyer" in node.verified_roles
    assert node.response_history_weight == 0.5
    assert node.stale_contact is False
    assert node.liquidity_preferences == preferences


def test_opportunity_lifecycle_has_all_operational_dispositions_and_expiry() -> None:
    service = OpportunityLifecycleService()
    opportunity_id = uuid4()
    assert service.disposition_to_state(
        opportunity_id=opportunity_id,
        disposition=OperatorDisposition.ARCHIVE,
        evidence_refs=evidence(),
        rationale="not current",
    ).state == LifecycleState.ARCHIVED
    assert service.disposition_to_state(
        opportunity_id=opportunity_id,
        disposition=OperatorDisposition.AUTOMATE,
        evidence_refs=evidence(),
        rationale="repeatable verification",
    ).state == LifecycleState.AUTOMATED
    assert service.disposition_to_state(
        opportunity_id=opportunity_id,
        disposition=OperatorDisposition.DELEGATE,
        evidence_refs=evidence(),
        rationale="human relationship owner required",
    ).state == LifecycleState.DELEGATED
    non_monetizable = service.disposition_to_state(
        opportunity_id=opportunity_id,
        disposition=OperatorDisposition.NON_MONETIZABLE,
        evidence_refs=evidence(),
        rationale="no payer or payment path",
    )
    non_monetizable.expires_at = utcnow() - timedelta(seconds=1)
    assert non_monetizable.state == LifecycleState.KILLED
    assert service.expire_if_stale(non_monetizable) is True


def test_transaction_and_source_lifecycles_fail_closed() -> None:
    tx_service = TransactionLifecycleService()
    tx_id = uuid4()
    assert tx_service.close(tx_id, 10000, 7000, evidence()).outcome == LifecycleState.CLOSED
    assert tx_service.loss(tx_id, evidence()).outcome == LifecycleState.LOST
    assert tx_service.abandon(tx_id, evidence()).outcome == LifecycleState.ABANDONED

    source_service = SourcePolicyService()
    public_policy = SourceActivationPolicy(
        "public-registry",
        SourceRightsClass.PUBLIC_SAFE,
        CollectionMethod.PUBLIC_API,
        evidence(),
        "CA-ON",
        True,
        True,
        True,
    )
    pii_policy = SourceActivationPolicy(
        "pii-feed",
        SourceRightsClass.PII_SENSITIVE,
        CollectionMethod.PII_COLLECTION,
        evidence(),
        "US-NY",
        True,
        True,
        True,
    )
    assert source_service.activation_verdict(public_policy) == ConformanceVerdict.GO
    assert source_service.activation_verdict(pii_policy) == ConformanceVerdict.HOLD


def test_movement_detection_and_profit_attribution_chain_are_complete() -> None:
    signal = MovementChangeDetector().detect(
        entity_id=uuid4(),
        before=10,
        after=17,
        evidence_refs=evidence(),
    )
    assert signal.direction == "up"
    assert signal.magnitude == 7

    profit = ProfitEvent(uuid4(), 10000, 2000, 500, 250, "CAD", evidence())
    normalized = ProfitNormalizationService().normalize(
        profit,
        reporting_currency="USD",
        fx_rate=0.75,
    )
    assert normalized.net_profit == 5437.5
    chain = CausalAttributionChain(
        profit.id,
        profit.transaction_id,
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        "source:registry",
        uuid4(),
        uuid4(),
        0.88,
        evidence(),
    )
    assert AttributionPromotionService().promotion_verdict(chain) == ConformanceVerdict.GO


def test_capital_and_compounding_lifecycles_require_evidence_and_resource_estimates() -> None:
    capital = CapitalLifecycleService()
    deployment = capital.deploy(
        capital_state_id=uuid4(),
        opportunity_id=uuid4(),
        amount=1500,
        currency="CAD",
        evidence_refs=evidence(),
    )
    reconciliation = capital.reconcile(
        deployment,
        returned_amount=2200,
        net_profit=700,
        evidence_refs=evidence(),
    )
    assert deployment.state == LifecycleState.DEPLOYED
    assert reconciliation.state == LifecycleState.RECONCILED

    compounding = CompoundingEmergenceService()
    pattern = compounding.detect_repeated_pattern(
        pattern_key="buyer-matching",
        transaction_ids=[uuid4(), uuid4()],
        payer_ids=[uuid4()],
        evidence_refs=evidence(),
    )
    score = compounding.score_asset(
        asset_key="verified-buyer-database",
        evidence_count=8,
        payer_count=3,
        expected_value=50000,
        resource_estimate=10000,
        evidence_refs=evidence(),
    )
    candidate = compounding.create_build_candidate(
        candidate_type="owned_platform",
        pattern=pattern,
        resource_estimate=10000,
    )
    assert score.score == 120.0
    assert candidate.repeated_evidence is True
    assert candidate.payer_evidence is True


def test_fixture_universe_and_operator_surface_are_complete() -> None:
    fixture = DeterministicFixtureFamily(
        fixture_id="mod_008_015_complete_fixture_universe",
        scenarios=sorted(FixtureUniverseValidator.required_scenarios),
        expected_transitions=["pressure.supported->active", "capital.deployed->reconciled"],
        expected_negative_gates=["prohibited_source_hold", "missing_evidence_transition_hold"],
        expected_operator_panels=sorted(OperatorSurfaceConformanceService.required_panels),
        evidence_refs=evidence(),
    )
    surface = OperatorSurfaceRequirement(
        surface_id="mod_008_015_complete_operator_surface",
        panels=fixture.expected_operator_panels,
        approval_gates=["external_action_approval", "capital_deployment_approval"],
        evidence_refs=evidence(),
    )
    statuses = [
        FixtureUniverseValidator().validate(fixture),
        OperatorSurfaceConformanceService().verdict(surface),
    ]
    assert summarize_mod_008_015_verdict(statuses) == ConformanceVerdict.GO
