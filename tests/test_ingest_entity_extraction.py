"""IngestService + entity extraction: opt-in default-off, budget-bounded,
and that a real extraction can turn a non-actionable classified signal
into a queued, approval-gated revenue action.
"""

from __future__ import annotations

import json

from brain.connectors.protocol import RawObservationItem, utcnow
from brain.connectors.rss import RssConnector
from brain.connectors.service import IngestService
from brain.memory import InMemoryBrainStore
from brain.money_spine import RevenueActionState, RevenueExecutionSpine
from brain.reasoning import ReasonResult


def _rfp_item() -> RawObservationItem:
    claim = "Municipal government issues Request for Proposal for qualified vendors"
    return RawObservationItem(
        title="City issues RFP", content=claim, claim=claim,
        source_url="https://example.com/rfp", item_id="i1", content_hash="h1",
        observed_at=utcnow(), confidence=0.6,
    )


class _FakeReasoner:
    """Returns a fixed, fully-enriched extraction on every call."""

    def __init__(self) -> None:
        self.calls = 0

    def reason(self, request):
        self.calls += 1
        payload = {
            "named_buyer": {"value": "City Procurement Office", "confidence": 0.9},
            "decision_maker": {"value": "Procurement Director", "confidence": 0.85},
            "visible_pain": {"value": "Current vendor contract expiring", "confidence": 0.8},
            "urgency_reason": {"value": "Bid window closes in 10 days", "confidence": 0.8},
            "payment_path": {"value": "Vendor bid support retainer", "confidence": 0.75},
            "contact_channel": {"value": "procurement@example.gov", "confidence": 0.9},
        }
        return ReasonResult(content=json.dumps(payload), confidence=0.5,
                             task_type=request.task_type, model_id="fake")


class _NeverCalledReasoner:
    def reason(self, request):
        raise AssertionError("entity extractor should not have been invoked")


def test_entity_extraction_off_by_default():
    svc = IngestService(connectors=[RssConnector()], revenue=RevenueExecutionSpine())
    assert svc.entity_extractor is None
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")
    action_id = svc._maybe_queue_revenue_action(source, _rfp_item())
    # No extractor configured -> falls back to scored-only, exactly like
    # before this feature existed.
    assert action_id is None


def test_entity_extraction_turns_non_actionable_signal_into_queued_action():
    revenue = RevenueExecutionSpine()
    reasoner = _FakeReasoner()
    svc = IngestService(connectors=[RssConnector()], revenue=revenue, entity_extractor=reasoner)
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    action_id = svc._maybe_queue_revenue_action(source, _rfp_item())
    assert action_id is not None
    assert reasoner.calls == 1
    action = revenue.actions[list(revenue.actions)[0]]
    assert action.state == RevenueActionState.APPROVAL_REQUIRED
    assert action.lane_id == "procurement_rfp_match"


def test_entity_extraction_respects_batch_budget():
    revenue = RevenueExecutionSpine()
    reasoner = _FakeReasoner()
    svc = IngestService(
        connectors=[RssConnector()], revenue=revenue, entity_extractor=reasoner,
        max_extractions_per_batch=1,
    )
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    first = svc._maybe_queue_revenue_action(source, _rfp_item())
    assert first is not None
    assert reasoner.calls == 1

    # Second call in the same batch (no ingest_due_sources reset in
    # between) should not extract again — budget exhausted.
    second_item = RawObservationItem(
        title="City issues RFP 2", content="Request for Proposal for qualified vendors",
        claim="Request for Proposal for qualified vendors",
        source_url="https://example.com/rfp2", item_id="i2", content_hash="h2",
        observed_at=utcnow(), confidence=0.6,
    )
    second = svc._maybe_queue_revenue_action(source, second_item)
    assert second is None
    assert reasoner.calls == 1


def test_ingest_due_sources_resets_extraction_budget_per_batch():
    revenue = RevenueExecutionSpine()
    reasoner = _FakeReasoner()
    svc = IngestService(
        connectors=[RssConnector()], revenue=revenue, entity_extractor=reasoner,
        max_extractions_per_batch=1,
    )
    svc._extractions_this_batch = 1  # simulate budget exhausted from a prior batch
    svc.ingest_due_sources()
    assert svc._extractions_this_batch == 0


def test_extraction_failure_falls_back_to_scored_only_without_raising():
    class _RaisingReasoner:
        def reason(self, request):
            raise RuntimeError("upstream LLM outage")

    revenue = RevenueExecutionSpine()
    store = InMemoryBrainStore()
    svc = IngestService(
        connectors=[RssConnector()], revenue=revenue, event_store=store,
        entity_extractor=_RaisingReasoner(),
    )
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    action_id = svc._maybe_queue_revenue_action(source, _rfp_item())
    assert action_id is None
    events = [e for e in store.read_all() if e.event_type == "revenue.signal_scored"]
    assert len(events) == 1
    assert events[0].payload["actionable"] is False


def test_extractor_not_called_when_signal_already_actionable():
    """If the source already supplied enough via item.metadata,
    extraction is skipped entirely — no reason to spend a call."""
    revenue = RevenueExecutionSpine()
    svc = IngestService(
        connectors=[RssConnector()], revenue=revenue, entity_extractor=_NeverCalledReasoner(),
    )
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    item = _rfp_item()
    item.metadata.update({
        "named_buyer": "City Procurement Office",
        "decision_maker": "Procurement Director",
        "visible_pain": "Current vendor contract expiring",
        "urgency_reason": "Bid window closes in 10 days",
        "payment_path": "Vendor bid support retainer",
        "contact_channel": "procurement@example.gov",
    })
    action_id = svc._maybe_queue_revenue_action(source, item)
    assert action_id is not None
