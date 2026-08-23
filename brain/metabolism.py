from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID, uuid4

from .domain import utcnow
from .events import BrainEvent


@dataclass(slots=True)
class CapitalLedger:
    """The brain's food supply.

    Everything else the brain does — attention, curiosity, action selection —
    is ultimately in service of keeping `balance` above `survival_threshold`.
    Metabolism (existing, thinking, running compute, holding positions) burns
    balance every tick regardless of what the brain is doing; only a fed
    outcome pushes it back up. That asymmetry is what makes this hunger
    instead of just another scored variable.
    """

    balance: float
    burn_rate: float
    survival_threshold: float = 0.0
    warning_threshold: float = 0.0
    starving_since: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if self.warning_threshold < self.survival_threshold:
            self.warning_threshold = self.survival_threshold

    @property
    def is_starving(self) -> bool:
        return self.balance <= self.survival_threshold

    @property
    def is_hungry(self) -> bool:
        return self.balance <= self.warning_threshold

    @property
    def deficit_ratio(self) -> float:
        """0.0 = fully fed, 1.0 = at or below the survival threshold.

        Designed to be dropped directly into HomeostaticState.budget_pressure.
        """
        if self.balance >= self.warning_threshold:
            return 0.0
        if self.balance <= self.survival_threshold:
            return 1.0
        span = self.warning_threshold - self.survival_threshold
        return (self.warning_threshold - self.balance) / span


class MetabolismEngine:
    """Turns existence into hunger, and outcomes into food."""

    def metabolize(self, ledger: CapitalLedger, *, ticks: float = 1.0) -> tuple[CapitalLedger, list[BrainEvent]]:
        was_starving = ledger.is_starving
        updated = replace(ledger, balance=ledger.balance - ledger.burn_rate * ticks, updated_at=utcnow())
        events = [
            BrainEvent(
                "capital.metabolized",
                "capital_ledger",
                updated.id,
                {"burned": ledger.burn_rate * ticks, "balance": updated.balance, "deficit_ratio": updated.deficit_ratio},
            )
        ]
        if updated.is_starving and not was_starving:
            updated = replace(updated, starving_since=updated.updated_at)
            events.append(
                BrainEvent(
                    "capital.starvation",
                    "capital_ledger",
                    updated.id,
                    {"balance": updated.balance, "survival_threshold": updated.survival_threshold},
                )
            )
        return updated, events

    def feed(self, ledger: CapitalLedger, amount: float, *, source: str) -> tuple[CapitalLedger, BrainEvent]:
        was_starving = ledger.is_starving
        updated = replace(ledger, balance=ledger.balance + amount, updated_at=utcnow())
        recovered = was_starving and not updated.is_starving
        if recovered:
            updated = replace(updated, starving_since=None)
        event = BrainEvent(
            "capital.fed",
            "capital_ledger",
            updated.id,
            {
                "amount": amount,
                "source": source,
                "balance": updated.balance,
                "recovered_from_starvation": recovered,
            },
        )
        return updated, event

    def budget_pressure(self, ledger: CapitalLedger) -> float:
        """Maps ledger deficit onto HomeostaticState.budget_pressure's [0,1] scale
        so hunger flows into the existing HomeostasisEngine / scheduler without any
        new global state.
        """
        return ledger.deficit_ratio
