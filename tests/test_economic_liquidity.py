from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from brain.economic import (
    CommercialDisposition,
    CounterpartyProfile,
    CounterpartyRole,
    EconomicOpportunity,
    OpportunityType,
)
from brain.economic_liquidity import (
    CommercialPortfolioService,
    CounterpartyInteraction,
    CounterpartyLiquidityService,
    LiquidityPreference,
)
from brain.economic_runtime import InMemoryEconomicStore


def _opportunity(**overrides) -> EconomicOpportunity:
    values = {
        "kind": OpportunityType.SERVICE,
        "entity_id": uuid4(),
        "money_path_ids": [uuid4()],
        "gross_value": 10000.0,
        "net_value": 8000.0,
        "conversion_probability": 0.7,
        "urgency": 0.8,
        "access_advantage": 0.8,
        "evidence_confidence": 0.85,
        "repeatability": 0.6,
        "strategic_compounding_value": 0.6,
        "required_capital": 100.0,
        "required_operator_hours": 2.0,
        "legal_reputation_risk": 0.1,
        "operational_complexity": 0.3,
        "time_decay": 0.05,
    }
    values.update(overrides)
    return EconomicOpportunity(**values)


def test_liquidity_preference_and_interaction_require_evidence() -> None:
    store = InMemoryEconomicStore()
    service = CounterpartyLiquidityService(store)
    counterparty_id = uuid4()
    with pytest.raises(ValueError, match="liquidity_preference_requires_evidence"):
        service.save_preference(
            LiquidityPreference(counterparty_id, CounterpartyRole.BUYER)
        )
    with pytest.raises(ValueError, match="counterparty_interaction_requires_evidence"):
        service.record_interaction(
            CounterpartyInteraction(counterparty_id, "email", "none", False)
        )


def test_ranked_match_uses_preferences_response_history_explanation_and_provenance() -> None:
    store = InMemoryEconomicStore()
    service = CounterpartyLiquidityService(store)
    strong = CounterpartyProfile(
        entity_id=uuid4(),
        roles={CounterpartyRole.BUYER},
        budget_estimate=100000,
        trust=0.8,
        reachability=0.8,
        decision_authority=0.9,
        urgency=0.7,
        metadata={"evidence_refs": ["registry:buyer"]},
    )
    weak = CounterpartyProfile(
        entity_id=uuid4(),
        roles={CounterpartyRole.BUYER},
        budget_estimate=100000,
        trust=0.8,
        reachability=0.8,
        decision_authority=0.9,
        urgency=0.7,
        metadata={"evidence_refs": ["registry:weak"]},
    )
    store.put("counterparty", strong.id, strong)
    store.put("counterparty", weak.id, weak)
    service.save_preference(
        LiquidityPreference(
            strong.id,
            CounterpartyRole.BUYER,
            categories=["industrial"],
            geographies=["CA"],
            min_value=5000,
            max_value=200000,
            evidence_refs=["call:preference"],
        )
    )
    service.record_interaction(
        CounterpartyInteraction(
            strong.id,
            "email",
            "positive reply",
            True,
            response_seconds=3600,
            decision_maker_reached=True,
            positive_signal=True,
            evidence_refs=["email:reply"],
        )
    )
    service.record_interaction(
        CounterpartyInteraction(
            weak.id,
            "email",
            "ignored",
            False,
            negative_signal=True,
            evidence_refs=["email:no-response"],
        )
    )
    ranked = service.rank(
        CounterpartyRole.BUYER,
        category="industrial",
        geography="CA",
        value=25000,
    )
    assert ranked[0].counterparty_id == strong.id
    assert ranked[0].response_history_score > ranked[1].response_history_score
    assert ranked[0].explanation
    assert set(ranked[0].provenance) == {"call:preference", "email:reply"}


def test_commercial_disposition_supports_full_required_semantics() -> None:
    store = InMemoryEconomicStore()
    service = CommercialPortfolioService(store)

    kill = service.disposition(_opportunity(), qualified_payment_path=False)
    verify = service.disposition(
        _opportunity(evidence_confidence=0.4),
        qualified_payment_path=True,
        evidence_state="provisional",
    )
    automate = service.disposition(
        _opportunity(repeatability=0.95, operational_complexity=0.1, required_operator_hours=5),
        qualified_payment_path=True,
    )
    delegate = service.disposition(
        _opportunity(required_operator_hours=12, strategic_compounding_value=0.2),
        qualified_payment_path=True,
    )
    build = service.disposition(
        _opportunity(strategic_compounding_value=0.95, repeatability=0.8, required_operator_hours=2),
        qualified_payment_path=True,
    )
    act = service.disposition(_opportunity(), qualified_payment_path=True)
    watch = service.disposition(
        _opportunity(urgency=0.3, strategic_compounding_value=0.4),
        qualified_payment_path=True,
    )
    archived_opportunity = _opportunity()
    archived_opportunity.created_at = archived_opportunity.created_at - timedelta(days=180)
    archive = service.disposition(archived_opportunity, qualified_payment_path=True)

    assert {
        kill.disposition,
        verify.disposition,
        automate.disposition,
        delegate.disposition,
        build.disposition,
        act.disposition,
        watch.disposition,
        archive.disposition,
    } == set(CommercialDisposition)
    assert all(record.reasons for record in [kill, verify, automate, delegate, build, act, watch, archive])


def test_opportunity_decay_and_expiry_are_explicit_and_persistent() -> None:
    store = InMemoryEconomicStore()
    service = CommercialPortfolioService(store)
    opportunity = _opportunity()
    old_score = service.effective_score(opportunity)
    future = opportunity.created_at + timedelta(days=60)
    decayed = service.effective_score(opportunity, at=future, half_life_days=30)
    assert decayed < old_score

    opportunity.created_at = opportunity.created_at - timedelta(days=200)
    store.put("opportunity", opportunity.id, opportunity)
    expired = service.expire_due(archive_after_days=120)
    assert expired[0].opportunity_id == opportunity.id
    assert expired[0].disposition is CommercialDisposition.ARCHIVE
    assert store.list("opportunity_disposition")
