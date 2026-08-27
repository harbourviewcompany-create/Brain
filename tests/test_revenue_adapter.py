"""Revenue adapter: raw ingested observations -> RevenueSignal candidates."""

from __future__ import annotations

from brain.connectors.protocol import RawObservationItem, utcnow
from brain.connectors.revenue_adapter import (
    classify_money_lane,
    revenue_signal_from_observation,
)
from brain.connectors.service import IngestService
from brain.connectors.store import InMemoryConnectorRegistry
from brain.money_spine import RevenueActionState, RevenueExecutionSpine


def _item(title: str, claim: str, content: str = "", url: str = "https://example.com/x") -> RawObservationItem:
    return RawObservationItem(
        title=title,
        content=content or claim,
        claim=claim,
        source_url=url,
        item_id="item-1",
        content_hash="hash-1",
        observed_at=utcnow(),
        confidence=0.6,
    )


def test_classify_money_lane_procurement():
    item = _item("City issues RFP", "Municipal government issues Request for Proposal for waste services")
    assert classify_money_lane(item) == "procurement_rfp_match"


def test_classify_money_lane_buyer_seller():
    item = _item("Equipment for sale", "Manufacturer liquidating warehouse equipment, buyer needed")
    assert classify_money_lane(item) == "buyer_seller_match_sprint"


def test_classify_money_lane_high_intent_lead():
    item = _item("Founder post", "Looking for recommendations for a new vendor after switching from our old supplier")
    assert classify_money_lane(item) == "high_intent_lead_pack"


def test_classify_money_lane_returns_none_when_no_trigger():
    item = _item("Weather update", "It rained heavily in the region today")
    assert classify_money_lane(item) is None


def test_revenue_signal_from_observation_none_when_unclassified():
    item = _item("Weather update", "It rained heavily in the region today")
    assert revenue_signal_from_observation(item, source_id="demo") is None


def test_revenue_signal_from_observation_builds_conservative_signal():
    item = _item(
        "City issues RFP",
        "Municipal government issues Request for Proposal for qualified vendors",
        url="https://example.com/rfp",
    )
    signal = revenue_signal_from_observation(item, source_id="demo-source")
    assert signal is not None
    assert signal.money_lane_id == "procurement_rfp_match"
    assert signal.source_id == "demo-source"
    assert signal.evidence_refs == ["https://example.com/rfp"]
    # The adapter must never invent buyer/seller/payment specifics.
    assert signal.named_buyer is None
    assert signal.named_seller is None
    assert signal.payment_path is None
    assert signal.contact_channel is None
    assert signal.metadata["auto_classified"] is True


def test_unenriched_commercial_item_is_scored_not_fantasized_into_an_action():
    """An automated feed item with a commercial lane match but no real
    buyer/seller/contact info must NOT become an executable action —
    NoFantasyFilter should reject it, and it should still be visible via
    a revenue.signal_scored event rather than silently vanishing."""
    from brain.connectors.rss import RssConnector
    from brain.memory import InMemoryBrainStore

    revenue = RevenueExecutionSpine()
    registry = InMemoryConnectorRegistry()
    store = InMemoryBrainStore()
    svc = IngestService(registry=registry, revenue=revenue, event_store=store, connectors=[RssConnector()])

    commercial_item = _item(
        "City issues RFP",
        "Municipal government issues Request for Proposal for qualified vendors",
    )
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    action_id = svc._maybe_queue_revenue_action(source, commercial_item)
    assert action_id is None
    assert len(revenue.actions) == 0

    events = [e for e in store.read_all() if e.event_type == "revenue.signal_scored"]
    assert len(events) == 1
    assert events[0].payload["actionable"] is False
    assert "no_named_buyer_seller_or_decision_maker" in events[0].payload["rejection_reasons"]


def test_non_commercial_item_produces_no_signal_and_no_event():
    from brain.connectors.rss import RssConnector
    from brain.memory import InMemoryBrainStore

    revenue = RevenueExecutionSpine()
    store = InMemoryBrainStore()
    svc = IngestService(revenue=revenue, event_store=store, connectors=[RssConnector()])
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    non_commercial_item = _item("Weather update", "It rained heavily in the region today")
    action_id = svc._maybe_queue_revenue_action(source, non_commercial_item)
    assert action_id is None
    assert not [e for e in store.read_all() if e.event_type == "revenue.signal_scored"]


def test_enriched_commercial_item_queues_a_real_approval_required_action():
    """When a source actually supplies buyer/seller/contact specifics
    (e.g. a structured procurement portal), the adapter uses them — and
    only then does the item become a real, approval-gated action."""
    from brain.connectors.rss import RssConnector

    revenue = RevenueExecutionSpine()
    svc = IngestService(revenue=revenue, connectors=[RssConnector()])
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    enriched_item = _item(
        "City issues RFP",
        "Municipal government issues Request for Proposal for qualified vendors",
    )
    enriched_item.metadata.update({
        "named_buyer": "City of Example Procurement Office",
        "decision_maker": "Procurement Director",
        "visible_pain": "Current vendor contract expiring",
        "urgency_reason": "Bid window closes in 10 days",
        "payment_path": "Vendor bid support retainer",
        "contact_channel": "procurement@example.gov",
    })

    action_id = svc._maybe_queue_revenue_action(source, enriched_item)
    assert action_id is not None
    assert len(revenue.actions) == 1
    action = next(iter(revenue.actions.values()))
    assert action.state == RevenueActionState.APPROVAL_REQUIRED
    assert action.lane_id == "procurement_rfp_match"


def test_ingest_service_revenue_hook_never_raises_without_spine():
    from brain.connectors.rss import RssConnector

    svc = IngestService(connectors=[RssConnector()])
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")
    item = _item(
        "City issues RFP",
        "Municipal government issues Request for Proposal for qualified vendors",
    )
    assert svc._maybe_queue_revenue_action(source, item) is None
