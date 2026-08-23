from uuid import uuid4

from brain.economic import CounterpartyProfile, CounterpartyRole
from brain.economic_codec import decode, encode
from brain.economic_runtime import KillDecision
from brain.economic import CommercialDisposition


def test_codec_round_trips_enum_sets_and_uuids() -> None:
    profile = CounterpartyProfile(
        entity_id=uuid4(),
        roles={CounterpartyRole.BUYER, CounterpartyRole.INVESTOR},
        budget_estimate=100000,
        trust=0.8,
        reachability=0.9,
        decision_authority=1.0,
    )
    payload = encode(profile)
    hydrated = decode("counterparty", payload)
    assert isinstance(hydrated, CounterpartyProfile)
    assert hydrated.entity_id == profile.entity_id
    assert hydrated.roles == profile.roles


def test_codec_round_trips_kill_disposition_as_enum() -> None:
    decision = KillDecision(
        opportunity_id=uuid4(),
        disposition=CommercialDisposition.ACT_NOW,
        reasons=[],
        score=42.0,
        formula_run_id=uuid4(),
    )
    hydrated = decode("kill_decision", encode(decision))
    assert hydrated.disposition is CommercialDisposition.ACT_NOW


def test_codec_kind_fallback_supports_pre_class_metadata_rows() -> None:
    profile = CounterpartyProfile(
        entity_id=uuid4(),
        roles={CounterpartyRole.SELLER},
    )
    payload = encode(profile)
    payload.pop("__class__")
    hydrated = decode("counterparty", payload)
    assert isinstance(hydrated, CounterpartyProfile)
    assert CounterpartyRole.SELLER in hydrated.roles
