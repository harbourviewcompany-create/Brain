"""extract_revenue_entities: parsing, confidence gating, safety on bad input."""

from __future__ import annotations

import json

from brain.connectors.entity_extractor import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    extract_revenue_entities,
)
from brain.connectors.protocol import RawObservationItem, utcnow
from brain.reasoning import ReasonResult


def _item(claim: str = "City issues RFP for qualified vendors") -> RawObservationItem:
    return RawObservationItem(
        title="City issues RFP", content=claim, claim=claim,
        source_url="https://example.com/rfp", item_id="i1", content_hash="h1",
        observed_at=utcnow(), confidence=0.6,
    )


class _FakeReasoner:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0

    def reason(self, request):
        self.calls += 1
        return ReasonResult(content=self.content, confidence=0.5, task_type=request.task_type, model_id="fake")


def test_extract_revenue_entities_accepts_high_confidence_fields():
    reasoner = _FakeReasoner(json.dumps({
        "named_buyer": {"value": "City Procurement Office", "confidence": 0.9},
        "contact_channel": {"value": "buyer@example.gov", "confidence": 0.85},
        "payment_path": {"value": "guess with no basis", "confidence": 0.2},
    }))
    result = extract_revenue_entities(_item(), reasoner=reasoner)
    assert result["named_buyer"] == "City Procurement Office"
    assert result["contact_channel"] == "buyer@example.gov"
    # Below threshold -> dropped, even though the reasoner offered it.
    assert "payment_path" not in result
    assert result["extraction_confidence"]["payment_path"] == 0.2


def test_extract_revenue_entities_respects_custom_threshold():
    reasoner = _FakeReasoner(json.dumps({
        "named_buyer": {"value": "Maybe Co", "confidence": 0.5},
    }))
    strict = extract_revenue_entities(_item(), reasoner=reasoner, confidence_threshold=0.6)
    assert "named_buyer" not in strict
    lenient = extract_revenue_entities(_item(), reasoner=reasoner, confidence_threshold=0.4)
    assert lenient["named_buyer"] == "Maybe Co"


def test_extract_revenue_entities_ignores_unknown_fields():
    reasoner = _FakeReasoner(json.dumps({
        "made_up_field": {"value": "x", "confidence": 0.99},
        "named_buyer": {"value": "Real Co", "confidence": 0.9},
    }))
    result = extract_revenue_entities(_item(), reasoner=reasoner)
    assert "made_up_field" not in result
    assert result["named_buyer"] == "Real Co"


def test_extract_revenue_entities_handles_malformed_json_safely():
    reasoner = _FakeReasoner("not json at all { garbled")
    result = extract_revenue_entities(_item(), reasoner=reasoner)
    assert result == {"extraction_confidence": {}}


def test_extract_revenue_entities_handles_non_object_json_safely():
    reasoner = _FakeReasoner(json.dumps(["not", "a", "dict"]))
    result = extract_revenue_entities(_item(), reasoner=reasoner)
    assert result == {"extraction_confidence": {}}


def test_extract_revenue_entities_ignores_malformed_field_shapes():
    reasoner = _FakeReasoner(json.dumps({
        "named_buyer": "just a string, not {value, confidence}",
        "contact_channel": {"value": 12345, "confidence": 0.9},
        "decision_maker": {"value": "Ops Lead", "confidence": "not-a-number"},
    }))
    result = extract_revenue_entities(_item(), reasoner=reasoner)
    assert "named_buyer" not in result
    assert "contact_channel" not in result
    assert "decision_maker" not in result


def test_extract_revenue_entities_empty_object_is_a_valid_result():
    reasoner = _FakeReasoner("{}")
    result = extract_revenue_entities(_item(), reasoner=reasoner)
    assert result == {"extraction_confidence": {}}


def test_default_confidence_threshold_is_stricter_than_half():
    assert DEFAULT_CONFIDENCE_THRESHOLD >= 0.5
