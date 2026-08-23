from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from .economic import (
    CapitalState,
    CounterpartyProfile,
    EconomicAffordance,
    EconomicAsymmetry,
    EconomicOpportunity,
    MoneyPath,
    PressureEvent,
    RevenueAttribution,
    Transaction,
)
from .economic_attribution import ActionROI, OpportunityROI, SourceROI
from .economic_capital import CapitalAllocation, CurrencyNormalization
from .economic_compounding import (
    MarketplaceHypothesis,
    OfferHypothesis,
    ProductHypothesis,
    RepeatedTransactionPattern,
)
from .economic_runtime import (
    BusinessModelHypothesis,
    CompoundingAsset,
    EconomicROI,
    FeeControl,
    JurisdictionProfile,
    KillDecision,
    SourcePlane,
    SourceRightsProfile,
)
from .economic_sources import SourceCandidate, SourceDiscoveryProposal, SourceEconomics
from .economic_transaction import (
    DealRoom,
    ExclusivityRecord,
    FeeAgreement,
    IntroductionRecord,
    Mandate,
    OriginationEvidence,
    ReferralAgreement,
)


ECONOMIC_CLASSES: tuple[type[Any], ...] = (
    EconomicAsymmetry,
    PressureEvent,
    EconomicAffordance,
    MoneyPath,
    EconomicOpportunity,
    CounterpartyProfile,
    Transaction,
    RevenueAttribution,
    CapitalState,
    SourceRightsProfile,
    SourcePlane,
    JurisdictionProfile,
    KillDecision,
    FeeControl,
    EconomicROI,
    CompoundingAsset,
    BusinessModelHypothesis,
    SourceROI,
    ActionROI,
    OpportunityROI,
    CurrencyNormalization,
    CapitalAllocation,
    RepeatedTransactionPattern,
    OfferHypothesis,
    ProductHypothesis,
    MarketplaceHypothesis,
    SourceCandidate,
    SourceEconomics,
    SourceDiscoveryProposal,
    Mandate,
    IntroductionRecord,
    FeeAgreement,
    ReferralAgreement,
    ExclusivityRecord,
    OriginationEvidence,
    DealRoom,
)

CLASS_REGISTRY = {cls.__name__: cls for cls in ECONOMIC_CLASSES}

KIND_CLASS = {
    "asymmetry": EconomicAsymmetry,
    "pressure": PressureEvent,
    "affordance": EconomicAffordance,
    "money_path": MoneyPath,
    "opportunity": EconomicOpportunity,
    "counterparty": CounterpartyProfile,
    "transaction": Transaction,
    "revenue_attribution": RevenueAttribution,
    "capital_state": CapitalState,
    "source_rights": SourceRightsProfile,
    "source_plane": SourcePlane,
    "jurisdiction": JurisdictionProfile,
    "kill_decision": KillDecision,
    "fee_control": FeeControl,
    "economic_roi": EconomicROI,
    "compounding_asset": CompoundingAsset,
    "business_model": BusinessModelHypothesis,
    "source_roi": SourceROI,
    "action_roi": ActionROI,
    "opportunity_roi": OpportunityROI,
    "currency_normalization": CurrencyNormalization,
    "capital_allocation": CapitalAllocation,
    "repeated_transaction_pattern": RepeatedTransactionPattern,
    "offer_hypothesis": OfferHypothesis,
    "product_hypothesis": ProductHypothesis,
    "marketplace_hypothesis": MarketplaceHypothesis,
    "source_candidate": SourceCandidate,
    "source_economics": SourceEconomics,
    "source_discovery_proposal": SourceDiscoveryProposal,
    "mandate": Mandate,
    "introduction_record": IntroductionRecord,
    "fee_agreement": FeeAgreement,
    "referral_agreement": ReferralAgreement,
    "exclusivity_record": ExclusivityRecord,
    "origination_evidence": OriginationEvidence,
    "deal_room": DealRoom,
}


def encode(value: Any) -> Any:
    if is_dataclass(value):
        payload = {field.name: encode(getattr(value, field.name)) for field in fields(value)}
        payload["__class__"] = type(value).__name__
        return payload
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, set):
        return [encode(item) for item in sorted(value, key=str)]
    if isinstance(value, dict):
        return {str(key): encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(item) for item in value]
    return value


def decode(kind: str, payload: dict[str, Any]) -> Any:
    class_name = payload.get("__class__")
    cls = CLASS_REGISTRY.get(class_name) if class_name else KIND_CLASS.get(kind)
    if cls is None:
        return {key: value for key, value in payload.items() if key != "__class__"}
    return _construct(cls, payload)


def _construct(cls: type[Any], payload: dict[str, Any]) -> Any:
    hints = get_type_hints(cls)
    kwargs = {}
    for field in fields(cls):
        if field.name not in payload:
            continue
        kwargs[field.name] = _convert(payload[field.name], hints.get(field.name, Any))
    return cls(**kwargs)


def _convert(value: Any, annotation: Any) -> Any:
    if value is None:
        return None
    if annotation is Any:
        return value
    if annotation is UUID:
        return value if isinstance(value, UUID) else UUID(str(value))
    if annotation is datetime:
        return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, UnionType):
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return _convert(value, non_none[0])
        for candidate in non_none:
            try:
                return _convert(value, candidate)
            except (TypeError, ValueError):
                continue
        return value
    if origin is list:
        item_type = args[0] if args else Any
        return [_convert(item, item_type) for item in value]
    if origin is set:
        item_type = args[0] if args else Any
        return {_convert(item, item_type) for item in value}
    if origin is dict:
        key_type, value_type = args if len(args) == 2 else (Any, Any)
        return {
            _convert(key, key_type): _convert(item, value_type)
            for key, item in value.items()
        }
    if isinstance(annotation, type) and is_dataclass(annotation) and isinstance(value, dict):
        return _construct(annotation, value)
    return value
