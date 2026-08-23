from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


class AsymmetryType(StrEnum):
    INFORMATION = "information"
    TIMING = "timing"
    ACCESS = "access"
    TRUST = "trust"
    LIQUIDITY = "liquidity"
    EXECUTION = "execution"
    COMPLIANCE = "compliance"
    FRAGMENTATION = "fragmentation"
    PRICING = "pricing"
    CAPABILITY = "capability"
    ATTENTION = "attention"
    RELATIONSHIP = "relationship"


class PressureType(StrEnum):
    CASH = "cash"
    INVENTORY = "inventory"
    HIRING = "hiring"
    COMPLIANCE = "compliance"
    TIME = "time"
    REGULATORY = "regulatory"
    COMPETITIVE = "competitive"
    CUSTOMER = "customer"
    SUPPLY = "supply"
    DEMAND = "demand"
    DEBT = "debt"
    REPUTATION = "reputation"
    EXPANSION = "expansion"
    EXIT = "exit"
    OPERATIONAL = "operational"
    TECHNOLOGY = "technology"
    DISTRIBUTION = "distribution"
    LICENSING = "licensing"
    RELATIONSHIP = "relationship"


class MoneyVerb(StrEnum):
    BUY = "buy"
    SELL = "sell"
    BROKER = "broker"
    REFER = "refer"
    RECRUIT = "recruit"
    SOURCE = "source"
    VERIFY = "verify"
    PACKAGE = "package"
    AUTOMATE = "automate"
    ADVISE = "advise"
    LICENSE = "license"
    PUBLISH = "publish"
    INTRODUCE = "introduce"
    FINANCE = "finance"
    AGGREGATE = "aggregate"
    ARBITRAGE = "arbitrage"
    RESELL = "resell"
    MONITOR = "monitor"
    NEGOTIATE = "negotiate"
    MATCH = "match"
    BUILD = "build"
    ACQUIRE = "acquire"
    RENT = "rent"
    LEASE = "lease"
    LIQUIDATE = "liquidate"
    CONSOLIDATE = "consolidate"
    INSURE = "insure"
    CERTIFY = "certify"
    TRAIN = "train"
    ROUTE = "route"
    RANK = "rank"
    ALERT = "alert"


class OpportunityType(StrEnum):
    MICRO = "micro"
    SERVICE = "service"
    BROKERAGE = "brokerage"
    ARBITRAGE = "arbitrage"
    RECRUITING = "recruiting"
    PROCUREMENT = "procurement"
    MARKET_ENTRY = "market_entry"
    DISTRESS = "distress"
    EXPANSION = "expansion"
    SUPPLY_GAP = "supply_gap"
    DEMAND_GAP = "demand_gap"
    AUTOMATION = "automation"
    ACQUISITION = "acquisition"
    INVESTMENT = "investment"
    RELATIONSHIP = "relationship"
    DATA_PRODUCT = "data_product"
    MARKETPLACE = "marketplace"
    STRATEGIC_ASSET = "strategic_asset"


class PaymentModel(StrEnum):
    FINDERS_FEE = "finders_fee"
    REFERRAL_FEE = "referral_fee"
    RETAINER = "retainer"
    PROJECT_FEE = "project_fee"
    SUCCESS_FEE = "success_fee"
    BROKERAGE_SPREAD = "brokerage_spread"
    COMMISSION = "commission"
    SUBSCRIPTION = "subscription"
    SPONSORSHIP = "sponsorship"
    LISTING_FEE = "listing_fee"
    DATA_PRODUCT = "data_product"
    LEAD_PACK = "lead_pack"
    REVENUE_SHARE = "revenue_share"
    EQUITY = "equity"
    OPTION = "option"
    EXCLUSIVE_MANDATE = "exclusive_mandate"
    PAID_INTRODUCTION = "paid_introduction"
    IMPLEMENTATION_FEE = "implementation_fee"
    MAINTENANCE_FEE = "maintenance_fee"
    LICENSING_FEE = "licensing_fee"
    MARKETPLACE_TAKE_RATE = "marketplace_take_rate"


class CounterpartyRole(StrEnum):
    BUYER = "buyer"
    SELLER = "seller"
    SUPPLIER = "supplier"
    DISTRIBUTOR = "distributor"
    IMPORTER = "importer"
    EXPORTER = "exporter"
    INVESTOR = "investor"
    LENDER = "lender"
    OPERATOR = "operator"
    RECRUITING_CLIENT = "recruiting_client"
    CANDIDATE = "candidate"
    CONSULTANT = "consultant"
    BROKER = "broker"
    FACILITY_OWNER = "facility_owner"
    MANUFACTURER = "manufacturer"
    SERVICE_PROVIDER = "service_provider"


class CommercialDisposition(StrEnum):
    ACT_NOW = "act_now"
    VERIFY_FIRST = "verify_first"
    WATCH = "watch"
    ARCHIVE = "archive"
    KILL = "kill"
    AUTOMATE = "automate"
    DELEGATE = "delegate"
    BUILD_AS_ASSET = "build_as_asset"


@dataclass(slots=True)
class EconomicAsymmetry:
    entity_id: UUID
    kind: AsymmetryType
    magnitude: float
    confidence: float
    evidence_ids: list[UUID] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PressureEvent:
    entity_id: UUID
    kind: PressureType
    magnitude: float
    confidence: float
    direction: str = "increasing"
    evidence_ids: list[UUID] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    valid_until: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EconomicAffordance:
    entity_id: UUID
    verb: MoneyVerb
    rationale: str
    confidence: float
    evidence_ids: list[UUID] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class MoneyPath:
    verb: MoneyVerb
    payment_model: PaymentModel
    buyer_entity_id: UUID | None
    expected_gross_value: float
    expected_net_value: float
    time_to_cash_days: float
    conversion_probability: float
    collection_risk: float = 0.0
    fee_protection_required: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EconomicOpportunity:
    kind: OpportunityType
    entity_id: UUID
    money_path_ids: list[UUID]
    gross_value: float
    net_value: float
    conversion_probability: float
    urgency: float
    access_advantage: float
    evidence_confidence: float
    repeatability: float
    strategic_compounding_value: float
    required_capital: float
    required_operator_hours: float
    legal_reputation_risk: float
    operational_complexity: float
    time_decay: float = 0.0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def score(self) -> float:
        """Risk-adjusted economic priority score.

        Scores are intentionally deterministic and bounded by a stabilizing denominator.
        Formula registration/trace persistence is handled by the runtime formula service;
        this method is the pure calculation primitive used by tests and that service.
        """
        positive = (
            max(self.net_value, 0.0)
            * self.conversion_probability
            * self.urgency
            * self.access_advantage
            * self.evidence_confidence
            * self.repeatability
            * self.strategic_compounding_value
        )
        denominator = (
            1.0
            + max(self.required_capital, 0.0)
            + max(self.required_operator_hours, 0.0)
            + max(self.legal_reputation_risk, 0.0)
            + max(self.operational_complexity, 0.0)
            + max(self.time_decay, 0.0)
        )
        return positive / denominator


@dataclass(slots=True)
class CounterpartyProfile:
    entity_id: UUID
    roles: set[CounterpartyRole]
    needs: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    budget_estimate: float | None = None
    urgency: float = 0.0
    trust: float = 0.5
    reachability: float = 0.0
    decision_authority: float = 0.0
    response_rate: float | None = None
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Transaction:
    opportunity_id: UUID
    buyer_entity_id: UUID | None
    seller_entity_id: UUID | None
    payment_model: PaymentModel
    expected_revenue: float
    expected_profit: float
    capital_at_risk: float
    fee_protected: bool
    status: str = "detected"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RevenueAttribution:
    transaction_id: UUID
    opportunity_id: UUID
    source_ids: list[str]
    gross_revenue: float
    net_profit: float
    operator_hours: float
    data_compute_cost: float
    attribution_confidence: float
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CapitalState:
    available_capital: float
    reserved_capital: float = 0.0
    risk_capital: float = 0.0
    operating_budget: float = 0.0
    reinvestment_budget: float = 0.0
    currency: str = "USD"
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def deployable_capital(self) -> float:
        return max(self.available_capital - self.reserved_capital, 0.0)
