"""Bridges ingested sensory observations into the money spine.

This closes the gap between ``IngestService`` (real sources -> sensory
inbox beliefs) and ``MoneySpineService`` / ``RevenueExecutionSpine``
(commercial scoring -> approval-gated action). Before this module existed,
nothing in the ingest path ever constructed a ``RevenueSignal`` — a human
had to hand-type one through the API.

Design intent, matching ``NoFantasyFilter``: this adapter is deliberately
conservative. It only proposes a money lane when the observation contains
an explicit trigger phrase for that lane, and it never invents a named
buyer, seller, or payment path that was not present in the source text.
An observation that doesn't clear the bar simply produces no signal —
it stays a belief in the cognition loop, not a fantasy in the revenue
queue. Fields the adapter cannot responsibly infer (named_buyer,
named_seller, payment_path, contact_channel) are left as ``None`` on
purpose, so ``NoFantasyFilter``/``MoneySpineService.score_signal`` will
correctly mark most auto-classified signals as non-actionable until a
human or a later extraction pass enriches them with real specifics.
"""
from __future__ import annotations

from typing import Any

from ..money_spine import RevenueSignal
from .protocol import RawObservationItem

# Lane trigger phrases are intentionally narrow. Widening this list
# expands recall at the cost of precision — err toward missing a real
# opportunity over manufacturing a fake one.
LANE_TRIGGERS: dict[str, tuple[str, ...]] = {
    "high_intent_lead_pack": (
        "looking for recommendations",
        "need help with vendor",
        "switching from",
        "any recommendations for",
        "looking for a supplier",
    ),
    "buyer_seller_match_sprint": (
        "for sale",
        "liquidating",
        "buyer needed",
        "seller needed",
        "wanted supplier",
        "closing sale",
    ),
    "procurement_rfp_match": (
        "request for proposal",
        "rfp",
        "tender",
        "invitation to bid",
        "qualified vendors",
    ),
}


def classify_money_lane(item: RawObservationItem) -> str | None:
    """Return the first money lane whose trigger phrases match the item, or None."""
    haystack = f"{item.title} {item.claim} {item.content}".lower()
    for lane_id, triggers in LANE_TRIGGERS.items():
        if any(trigger in haystack for trigger in triggers):
            return lane_id
    return None


# Enrichment fields the adapter will use *if a connector actually supplies
# them* on item.metadata (e.g. a structured procurement portal or a source
# registry row with real contact data). The adapter never fabricates these
# — it only reads them if a real upstream source populated them.
_ENRICHMENT_FIELDS = (
    "named_buyer",
    "named_seller",
    "decision_maker",
    "visible_pain",
    "urgency_reason",
    "payment_path",
    "contact_channel",
)


def revenue_signal_from_observation(
    item: RawObservationItem,
    *,
    source_id: str,
    lane_id: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> RevenueSignal | None:
    """Attempt to build a RevenueSignal from a raw ingested observation.

    Returns None when no money lane can be responsibly inferred — this is
    the expected, common case, not an error path. When a lane *is*
    inferred but the source provided no buyer/seller/contact specifics,
    the returned signal will still exist but will typically fail
    NoFantasyFilter — that's intentional: the signal is a candidate for
    human or downstream-extraction enrichment, not a ready-to-act lead.
    """
    resolved_lane = lane_id or classify_money_lane(item)
    if resolved_lane is None:
        return None

    metadata = {
        "auto_classified": True,
        "classification_source": "revenue_adapter.classify_money_lane",
        "item_id": item.item_id,
        "observed_at": item.observed_at.isoformat(),
        **(extra_metadata or {}),
    }

    enrichment = {
        field: item.metadata.get(field)
        for field in _ENRICHMENT_FIELDS
        if isinstance(item.metadata.get(field), str) and item.metadata.get(field)
    }

    return RevenueSignal(
        raw_signal=item.claim or item.title,
        source_id=source_id,
        money_lane_id=resolved_lane,
        evidence_refs=[item.source_url] if item.source_url else [],
        commercial_value=0.4,
        confidence=min(0.6, max(0.2, item.confidence)),
        urgency=0.2,
        contactability=0.6 if enrichment.get("contact_channel") else 0.0,
        execution_difficulty=0.6,
        legal_access_risk=0.0,
        time_delay=0.3,
        metadata=metadata,
        **enrichment,
    )
