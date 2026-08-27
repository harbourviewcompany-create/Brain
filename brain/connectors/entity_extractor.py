"""Evidence-grounded entity extraction for auto-classified revenue signals.

The extractor is deliberately conservative. Model output is never trusted merely
because the model assigns itself a high confidence. Every accepted field must carry
an exact supporting quote found in the source, the extracted value itself must be
verbatim inside that quote, and confidence must be finite and inside 0.0-1.0.
"""
from __future__ import annotations

import json
import math
from typing import Any

from ..reasoning import ReasonRequest, Reasoner
from .protocol import RawObservationItem

EXTRACTABLE_FIELDS = (
    "named_buyer",
    "named_seller",
    "decision_maker",
    "visible_pain",
    "urgency_reason",
    "payment_path",
    "contact_channel",
)

DEFAULT_CONFIDENCE_THRESHOLD = 0.55


def _normalized_text(value: str) -> str:
    """Normalize case and whitespace for deterministic containment checks."""
    return " ".join(value.split()).casefold()


def _empty_result() -> dict[str, Any]:
    return {"extraction_confidence": {}, "extraction_provenance": {}}


def extract_revenue_entities(
    item: RawObservationItem,
    *,
    reasoner: Reasoner,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Extract commercial facts only when the source proves the exact value.

    Every accepted field must have a verbatim ``evidence_quote`` from the source,
    and the normalized extracted ``value`` must itself occur inside that quote.
    This prevents a model from pairing an invented value with an unrelated real
    quote to satisfy the grounding gate.
    """
    text = f"{item.title}\n{item.claim}\n{item.content}".strip()
    bounded_text = text[:4000]
    request = ReasonRequest(
        task_type="revenue_entity_extraction",
        prompt=bounded_text,
        context={"raw_text": bounded_text, "source_url": item.source_url},
        max_tokens=450,
    )
    try:
        result = reasoner.reason(request)
        parsed = json.loads(result.content)
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return _empty_result()

    if not isinstance(parsed, dict):
        return _empty_result()

    source_normalized = _normalized_text(bounded_text)
    accepted: dict[str, Any] = {}
    confidences: dict[str, float] = {}
    provenance: dict[str, dict[str, Any]] = {}

    for field_name in EXTRACTABLE_FIELDS:
        raw = parsed.get(field_name)
        if not isinstance(raw, dict):
            continue

        value = raw.get("value")
        evidence_quote = raw.get("evidence_quote")
        confidence = raw.get("confidence")
        if not isinstance(value, str) or not value.strip():
            continue
        if not isinstance(evidence_quote, str) or not evidence_quote.strip():
            continue

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(confidence_value) or not 0.0 <= confidence_value <= 1.0:
            continue

        clean_value = value.strip()
        quote = evidence_quote.strip()
        quote_normalized = _normalized_text(quote)
        if quote_normalized not in source_normalized:
            continue
        if _normalized_text(clean_value) not in quote_normalized:
            continue

        confidences[field_name] = confidence_value
        if confidence_value < confidence_threshold:
            continue

        accepted[field_name] = clean_value
        provenance[field_name] = {
            "confidence": confidence_value,
            "evidence_quote": quote,
            "model_id": str(getattr(result, "model_id", "unknown")),
            "source_url": item.source_url,
        }

    accepted["extraction_confidence"] = confidences
    accepted["extraction_provenance"] = provenance
    return accepted
