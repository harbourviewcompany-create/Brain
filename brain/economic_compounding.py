from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .economic_runtime import EconomicObjectState, EconomicStore


class CompoundingKind(StrEnum):
    BUYER_DATABASE = "buyer_database"
    SELLER_DATABASE = "seller_database"
    CONTACT_GRAPH = "contact_graph"
    PRICING_BENCHMARK = "pricing_benchmark"
    MARKET_MAP = "market_map"
    SOURCE_LIBRARY = "source_library"
    PROPRIETARY_DATASET = "proprietary_dataset"
    WORKFLOW = "workflow"
    DISTRIBUTION = "distribution"
    MARKETPLACE_LIQUIDITY = "marketplace_liquidity"
    REPUTATION = "reputation"


@dataclass(slots=True)
class RepeatedTransactionPattern:
    key: str
    transaction_ids: list[UUID]
    payer_entity_ids: list[UUID]
    problem_pattern: str
    solution_pattern: str
    net_profit_total: float
    id: UUID = field(default_factory=uuid4)

    @property
    def occurrence_count(self) -> int:
        return len(self.transaction_ids)

    @property
    def unique_payer_count(self) -> int:
        return len(set(self.payer_entity_ids))


@dataclass(slots=True)
class OfferHypothesis:
    pattern_id: UUID
    name: str
    payment_mechanism: str
    expected_unit_net_value: float
    evidence_count: int
    payer_count: int
    status: EconomicObjectState = EconomicObjectState.OBSERVED
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ProductHypothesis:
    offer_id: UUID
    name: str
    repeatable_delivery: bool
    automation_fraction: float
    expected_margin: float
    status: EconomicObjectState = EconomicObjectState.OBSERVED
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class MarketplaceHypothesis:
    pattern_id: UUID
    category: str
    buyer_count: int
    seller_count: int
    successful_matches: int
    paid_matches: int
    expected_take_rate: float
    status: EconomicObjectState = EconomicObjectState.OBSERVED
    id: UUID = field(default_factory=uuid4)


class CompoundingService:
    """MOD-015 productization and marketplace emergence over attributed transaction history."""

    def __init__(self, store: EconomicStore) -> None:
        self.store = store

    def register_pattern(self, pattern: RepeatedTransactionPattern) -> RepeatedTransactionPattern:
        self.store.put("repeated_transaction_pattern", pattern.id, pattern)
        return pattern

    def propose_offer(
        self,
        pattern: RepeatedTransactionPattern,
        *,
        name: str,
        payment_mechanism: str,
    ) -> OfferHypothesis:
        unit_value = pattern.net_profit_total / max(pattern.occurrence_count, 1)
        offer = OfferHypothesis(
            pattern_id=pattern.id,
            name=name,
            payment_mechanism=payment_mechanism,
            expected_unit_net_value=unit_value,
            evidence_count=pattern.occurrence_count,
            payer_count=pattern.unique_payer_count,
        )
        if offer.evidence_count >= 3 and offer.payer_count >= 2 and unit_value > 0:
            offer.status = EconomicObjectState.VALIDATED
        self.store.put("offer_hypothesis", offer.id, offer)
        return offer

    def propose_product(
        self,
        offer: OfferHypothesis,
        *,
        name: str,
        repeatable_delivery: bool,
        automation_fraction: float,
        expected_margin: float,
    ) -> ProductHypothesis:
        product = ProductHypothesis(
            offer_id=offer.id,
            name=name,
            repeatable_delivery=repeatable_delivery,
            automation_fraction=max(0.0, min(1.0, automation_fraction)),
            expected_margin=expected_margin,
        )
        if (
            offer.status is EconomicObjectState.VALIDATED
            and repeatable_delivery
            and expected_margin > 0
        ):
            product.status = EconomicObjectState.BUILD_CANDIDATE
        self.store.put("product_hypothesis", product.id, product)
        return product

    def propose_marketplace(
        self,
        pattern: RepeatedTransactionPattern,
        *,
        category: str,
        buyer_count: int,
        seller_count: int,
        successful_matches: int,
        paid_matches: int,
        expected_take_rate: float,
    ) -> MarketplaceHypothesis:
        hypothesis = MarketplaceHypothesis(
            pattern_id=pattern.id,
            category=category,
            buyer_count=buyer_count,
            seller_count=seller_count,
            successful_matches=successful_matches,
            paid_matches=paid_matches,
            expected_take_rate=expected_take_rate,
        )
        liquidity_ok = buyer_count >= 10 and seller_count >= 10
        transaction_proof = successful_matches >= 3 and paid_matches >= 1
        if liquidity_ok and transaction_proof and expected_take_rate > 0:
            hypothesis.status = EconomicObjectState.BUILD_CANDIDATE
        self.store.put("marketplace_hypothesis", hypothesis.id, hypothesis)
        return hypothesis

    def build_candidates(self) -> list[dict[str, Any]]:
        candidates = []
        for kind in ("product_hypothesis", "marketplace_hypothesis"):
            for obj in self.store.list(kind):
                if obj.status is EconomicObjectState.BUILD_CANDIDATE:
                    candidates.append(
                        {"kind": kind, "id": str(obj.id), "status": obj.status.value}
                    )
        return candidates
