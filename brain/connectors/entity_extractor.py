"""Evidence-grounded entity extraction for auto-classified revenue signals.

The extractor is deliberately conservative. Model output is never trusted merely
because the model assigns itself a high confidence. Every accepted field must carry
an exact supporting quote that is present in the source observation, and confidence
must be finite and inside the documented 0.0-1.0 range.
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
    """Normalize case and whitespace for deterministic quote containment."""
    return " ".join(value.split()).casefold()


def _empty_result() -> dict[str, Any]:
    return {"extraction_confidence": {}, "extraction_provenance": {}}


def extract_revenue_entities(
    item: RawObservationItem,
    *,
    reasoner: Reasoner,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Extract commercial facts only when source evidence proves each value.

    Expected model shape for each field::

        {
          "named_buyer": {
            "value": "City Procurement Office",
            "confidence": 0.91,
            "evidence_quote": "City Procurement Office is seeking bids"
          }
        }

    ``evidence_quote`` must occur in the source text after case/whitespace
    normalization. This makes prompt wording and model self-confidence advisory;
    unsupported output cannot satisfy ``NoFantasyFilter``.
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

        quote = evidence_quote.strip()
        if _normalized_text(quote) not in source_normalized:
            continue

        confidences[field_name] = confidence_value
        if confidence_value < confidence_threshold:
            continue

        accepted[field_name] = value.strip()
        provenance[field_name] = {
            "confidence": confidence_value,
            "evidence_quote": quote,
            "model_id": str(getattr(result, "model_id", "unknown")),
            "source_url": item.source_url,
        }

    accepted["extraction_confidence"] = confidences
    accepted["extraction_provenance"] = provenance
    return accepted
