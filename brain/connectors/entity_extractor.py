"""Real entity extraction for auto-classified revenue signals.

brain/connectors/revenue_adapter.py deliberately never invents a named
buyer, seller, or contact channel — it only reads enrichment fields a
source already supplied on item.metadata. That's correct and stays
correct. But it means most auto-classified signals from raw text feeds
(RSS, HTTP JSON) never clear NoFantasyFilter, because nothing upstream
ever populates those fields. This module is that upstream: it reads the
item's raw text and asks a reasoner (brain/reasoning.py's CortexReasoner
— local heuristic by default, a real LLM if BRAIN_LLM_URL/BRAIN_LLM_API_KEY
are configured) to extract only what's actually present in the text,
with a confidence score per field.

Design constraints, all deliberate:

  - Off by default. Nothing calls this automatically; IngestService only
    invokes it when constructed with `entity_extractor=` explicitly.
    Wiring it into the live ingest loop unconditionally would mean the
    system starts spending real API calls per ingested item without
    anyone having decided that's an acceptable cost/latency tradeoff.
  - Confidence-gated. A field below `confidence_threshold` is dropped,
    not passed through at a discount. NoFantasyFilter doesn't know how
    the field was produced — a low-confidence LLM guess is exactly as
    dangerous as a low-confidence human guess.
  - Budget-bounded. `max_extractions_per_batch` caps how many extraction
    calls a single ingest run will make, so a large batch of classified
    items can't silently trigger unbounded spend.
  - Never invents on parse failure. Malformed or missing JSON from the
    reasoner produces an empty result, not a crash and not a guess.
"""
from __future__ import annotations

import json
from typing import Any

from ..reasoning import ReasonRequest, Reasoner
from .protocol import RawObservationItem

#: Fields this module will ever populate. Matches revenue_adapter.py's
#: _ENRICHMENT_FIELDS exactly, so the merged result flows straight into
#: RevenueSignal construction without any renaming.
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


def extract_revenue_entities(
    item: RawObservationItem,
    *,
    reasoner: Reasoner,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Ask `reasoner` to extract commercial contact facts from `item`.

    Returns a dict shaped for merging into item.metadata (only string
    values for fields in EXTRACTABLE_FIELDS, at or above the confidence
    threshold) plus a nested "extraction_confidence" map recording every
    field's raw confidence for audit purposes, whether it cleared the
    bar or not. Never raises: a malformed response degrades to an empty
    result rather than propagating a parsing error into the ingest path.
    """
    text = f"{item.title}\n{item.claim}\n{item.content}".strip()
    request = ReasonRequest(
        task_type="revenue_entity_extraction",
        prompt=text[:4000],
        context={"raw_text": text[:4000], "source_url": item.source_url},
        max_tokens=300,
    )
    try:
        result = reasoner.reason(request)
        parsed = json.loads(result.content)
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return {"extraction_confidence": {}}

    if not isinstance(parsed, dict):
        return {"extraction_confidence": {}}

    accepted: dict[str, Any] = {}
    confidences: dict[str, float] = {}
    for field_name in EXTRACTABLE_FIELDS:
        raw = parsed.get(field_name)
        if not isinstance(raw, dict):
            continue
        value = raw.get("value")
        confidence = raw.get("confidence")
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            continue
        confidences[field_name] = confidence
        if confidence >= confidence_threshold:
            accepted[field_name] = value.strip()

    accepted["extraction_confidence"] = confidences
    return accepted
