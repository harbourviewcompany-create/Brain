from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .economic import CapitalState
from .economic_runtime import EconomicStore


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class CurrencyNormalization:
    source_currency: str
    target_currency: str
    source_amount: float
    fx_rate: float
    normalized_amount: float
    observed_at: datetime
    source_key: str
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CapitalAllocation:
    capital_state_id: UUID
    opportunity_id: UUID
    amount: float
    risk_fraction: float
    expected_net_value: float
    approved: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class CapitalStateService:
    """MOD-014 capital ledger; no allocation becomes deployable without approval."""

    def __init__(self, store: EconomicStore) -> None:
        self.store = store

    def save_state(self, state: CapitalState) -> CapitalState:
        if min(
            state.available_capital,
            state.reserved_capital,
            state.risk_capital,
            state.operating_budget,
            state.reinvestment_budget,
        ) < 0:
            raise ValueError("capital_state_cannot_be_negative")
        self.store.put("capital_state", state.id, state)
        return state

    def normalize_currency(
        self,
        *,
        amount: float,
        source_currency: str,
        target_currency: str,
        fx_rate: float,
        observed_at: datetime,
        source_key: str,
    ) -> CurrencyNormalization:
        if fx_rate <= 0:
            raise ValueError("fx_rate_must_be_positive")
        result = CurrencyNormalization(
            source_currency=source_currency,
            target_currency=target_currency,
            source_amount=amount,
            fx_rate=fx_rate,
            normalized_amount=amount * fx_rate,
            observed_at=observed_at,
            source_key=source_key,
        )
        self.store.put("currency_normalization", result.id, result)
        return result

    def propose_allocation(
        self,
        state: CapitalState,
        *,
        opportunity_id: UUID,
        amount: float,
        expected_net_value: float,
    ) -> CapitalAllocation:
        if amount <= 0:
            raise ValueError("allocation_amount_must_be_positive")
        if amount > state.deployable_capital:
            raise ValueError("allocation_exceeds_deployable_capital")
        risk_base = max(state.risk_capital, state.deployable_capital, 1.0)
        allocation = CapitalAllocation(
            capital_state_id=state.id,
            opportunity_id=opportunity_id,
            amount=amount,
            risk_fraction=amount / risk_base,
            expected_net_value=expected_net_value,
        )
        self.store.put("capital_allocation", allocation.id, allocation)
        return allocation

    def approve_allocation(
        self,
        state: CapitalState,
        allocation: CapitalAllocation,
        *,
        operator_approved: bool,
    ) -> CapitalState:
        if not operator_approved:
            raise ValueError("capital_allocation_requires_operator_approval")
        if allocation.amount > state.deployable_capital:
            raise ValueError("allocation_exceeds_deployable_capital")
        allocation.approved = True
        self.store.put("capital_allocation", allocation.id, allocation)
        updated = replace(
            state,
            reserved_capital=state.reserved_capital + allocation.amount,
            updated_at=utcnow(),
        )
        self.store.put("capital_state", updated.id, updated)
        return updated
