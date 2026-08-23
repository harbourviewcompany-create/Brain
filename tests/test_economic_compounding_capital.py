from datetime import UTC, datetime
from uuid import uuid4

import pytest

from brain.economic import CapitalState
from brain.economic_capital import CapitalStateService
from brain.economic_compounding import CompoundingService, RepeatedTransactionPattern
from brain.economic_runtime import EconomicObjectState, InMemoryEconomicStore


def test_capital_state_persists_and_allocation_requires_approval() -> None:
    store = InMemoryEconomicStore()
    service = CapitalStateService(store)
    state = service.save_state(
        CapitalState(
            available_capital=1000,
            reserved_capital=100,
            risk_capital=500,
            operating_budget=100,
            reinvestment_budget=200,
            currency="CAD",
        )
    )
    allocation = service.propose_allocation(
        state,
        opportunity_id=uuid4(),
        amount=200,
        expected_net_value=800,
    )
    with pytest.raises(ValueError, match="operator_approval"):
        service.approve_allocation(state, allocation, operator_approved=False)
    updated = service.approve_allocation(state, allocation, operator_approved=True)
    assert updated.reserved_capital == 300
    assert updated.deployable_capital == 700


def test_capital_allocation_cannot_exceed_deployable() -> None:
    service = CapitalStateService(InMemoryEconomicStore())
    state = service.save_state(CapitalState(available_capital=100, reserved_capital=90))
    with pytest.raises(ValueError, match="exceeds_deployable"):
        service.propose_allocation(
            state,
            opportunity_id=uuid4(),
            amount=11,
            expected_net_value=100,
        )


def test_currency_normalization_requires_explicit_rate_and_source() -> None:
    service = CapitalStateService(InMemoryEconomicStore())
    normalized = service.normalize_currency(
        amount=100,
        source_currency="EUR",
        target_currency="CAD",
        fx_rate=1.5,
        observed_at=datetime(2026, 8, 23, tzinfo=UTC),
        source_key="fixture-fx",
    )
    assert normalized.normalized_amount == 150
    assert normalized.source_key == "fixture-fx"


def test_offer_product_and_marketplace_emergence_use_repeat_proof() -> None:
    store = InMemoryEconomicStore()
    service = CompoundingService(store)
    payers = [uuid4(), uuid4(), uuid4()]
    pattern = service.register_pattern(
        RepeatedTransactionPattern(
            key="distressed-equipment",
            transaction_ids=[uuid4(), uuid4(), uuid4(), uuid4()],
            payer_entity_ids=[payers[0], payers[1], payers[2], payers[0]],
            problem_pattern="seller needs buyer",
            solution_pattern="verified buyer matching",
            net_profit_total=40000,
        )
    )
    offer = service.propose_offer(
        pattern,
        name="Equipment Disposition Sprint",
        payment_mechanism="success_fee",
    )
    product = service.propose_product(
        offer,
        name="Verified Equipment Liquidity Network",
        repeatable_delivery=True,
        automation_fraction=0.7,
        expected_margin=0.6,
    )
    marketplace = service.propose_marketplace(
        pattern,
        category="processing-equipment",
        buyer_count=12,
        seller_count=11,
        successful_matches=4,
        paid_matches=2,
        expected_take_rate=0.05,
    )
    assert offer.status is EconomicObjectState.VALIDATED
    assert product.status is EconomicObjectState.BUILD_CANDIDATE
    assert marketplace.status is EconomicObjectState.BUILD_CANDIDATE
    assert len(service.build_candidates()) == 2


def test_marketplace_does_not_emerge_without_liquidity() -> None:
    service = CompoundingService(InMemoryEconomicStore())
    pattern = service.register_pattern(
        RepeatedTransactionPattern(
            key="thin-market",
            transaction_ids=[uuid4(), uuid4(), uuid4()],
            payer_entity_ids=[uuid4(), uuid4()],
            problem_pattern="thin",
            solution_pattern="manual",
            net_profit_total=10000,
        )
    )
    marketplace = service.propose_marketplace(
        pattern,
        category="thin-market",
        buyer_count=3,
        seller_count=4,
        successful_matches=3,
        paid_matches=1,
        expected_take_rate=0.1,
    )
    assert marketplace.status is EconomicObjectState.OBSERVED
