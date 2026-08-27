"""IngestService + grounded entity extraction integration tests."""

from __future__ import annotations

import json

from brain.connectors.protocol import (
    ConnectorKind,
    FetchResult,
    FetchStatus,
    RawObservationItem,
    utcnow,
)
from brain.connectors.rss import RssConnector
from brain.connectors.service import IngestService
from brain.memory import InMemoryBrainStore
from brain.money_spine import RevenueActionState, RevenueExecutionSpine
from brain.reasoning import ReasonResult


def _rfp_item(*, item_id: str = "i1", content_hash: str = "h1") -> RawObservationItem:
    claim = (
        "City Procurement Office issued a Request for Proposal for qualified vendors. "
        "Procurement Director Jane Doe said the current vendor contract is expiring. "
        "Bid window closes in 10 days. Vendor bid support retainer is available. "
        "Contact procurement@example.gov for details."
    )
    return RawObservationItem(
        title="City issues RFP", content=claim, claim=claim,
        source_url="https://example.com/rfp", item_id=item_id, content_hash=content_hash,
        observed_at=utcnow(), confidence=0.6,
    )


class _FakeReasoner:
    """Returns fixed values with source-grounded evidence quotes."""

    def __init__(self) -> None:
        self.calls = 0

    def reason(self, request):
        self.calls += 1
        payload = {
            "named_buyer": {
                "value": "City Procurement Office",
                "confidence": 0.9,
                "evidence_quote": "City Procurement Office issued a Request for Proposal",
            },
            "decision_maker": {
                "value": "Procurement Director Jane Doe",
                "confidence": 0.85,
                "evidence_quote": "Procurement Director Jane Doe",
            },
            "visible_pain": {
                "value": "current vendor contract is expiring",
                "confidence": 0.8,
                "evidence_quote": "current vendor contract is expiring",
            },
            "urgency_reason": {
                "value": "Bid window closes in 10 days",
                "confidence": 0.8,
                "evidence_quote": "Bid window closes in 10 days",
            },
            "payment_path": {
                "value": "Vendor bid support retainer",
                "confidence": 0.75,
                "evidence_quote": "Vendor bid support retainer is available",
            },
            "contact_channel": {
                "value": "procurement@example.gov",
                "confidence": 0.9,
                "evidence_quote": "Contact procurement@example.gov for details",
            },
        }
        return ReasonResult(
            content=json.dumps(payload), confidence=0.5,
            task_type=request.task_type, model_id="fake-grounded-model",
        )


class _NeverCalledReasoner:
    def reason(self, request):
        raise AssertionError("entity extractor should not have been invoked")


class _Inbox:
    def enqueue(self, **kwargs):
        return f"inbox:{kwargs['source_key']}"


class _SequencedConnector:
    kind = ConnectorKind.RSS

    def __init__(self) -> None:
        self.calls = 0

    def supports(self, source):
        return source.kind == ConnectorKind.RSS

    def fetch(self, source):
        self.calls += 1
        item = _rfp_item(item_id=f"i{self.calls}", content_hash=f"h{self.calls}")
        return FetchResult(source_key=source.source_key, status=FetchStatus.SUCCESS, items=[item])


def test_entity_extraction_off_by_default():
    svc = IngestService(connectors=[RssConnector()], revenue=RevenueExecutionSpine())
    assert svc.entity_extractor is None
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")
    assert svc._maybe_queue_revenue_action(source, _rfp_item()) is None


def test_grounded_extraction_turns_non_actionable_signal_into_approval_action():
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
    provenance_refs = [ref for ref in action.evidence_refs if ref.startswith("extraction_provenance:")]
    assert len(provenance_refs) == 1
    provenance = json.loads(provenance_refs[0].split(":", 1)[1])
    assert provenance["named_buyer"]["evidence_quote"].startswith("City Procurement Office")
    assert provenance["named_buyer"]["model_id"] == "fake-grounded-model"


def test_source_provided_enrichment_is_never_overwritten_by_model_output():
    revenue = RevenueExecutionSpine()
    reasoner = _FakeReasoner()
    svc = IngestService(connectors=[RssConnector()], revenue=revenue, entity_extractor=reasoner)
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")
    item = _rfp_item()
    item.metadata["decision_maker"] = "Authoritative Procurement Director"

    action_id = svc._maybe_queue_revenue_action(source, item)
    assert action_id is not None
    action = revenue.actions[list(revenue.actions)[0]]
    assert action.target_contact == "Authoritative Procurement Director"
    provenance_ref = next(ref for ref in action.evidence_refs if ref.startswith("extraction_provenance:"))
    provenance = json.loads(provenance_ref.split(":", 1)[1])
    assert "decision_maker" not in provenance
    assert "contact_channel" in provenance


def test_entity_extraction_respects_one_operation_budget():
    revenue = RevenueExecutionSpine()
    reasoner = _FakeReasoner()
    svc = IngestService(
        connectors=[RssConnector()], revenue=revenue, entity_extractor=reasoner,
        max_extractions_per_batch=1,
    )
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")
    assert svc._maybe_queue_revenue_action(source, _rfp_item()) is not None
    assert reasoner.calls == 1

    second_item = _rfp_item(item_id="i2", content_hash="h2")
    assert svc._maybe_queue_revenue_action(source, second_item) is None
    assert reasoner.calls == 1


def test_ingest_due_sources_resets_extraction_budget_per_scheduled_operation():
    revenue = RevenueExecutionSpine()
    reasoner = _FakeReasoner()
    svc = IngestService(
        connectors=[RssConnector()], revenue=revenue, entity_extractor=reasoner,
        max_extractions_per_batch=1,
    )
    svc._extractions_this_batch = 1
    svc.ingest_due_sources()
    assert svc._extractions_this_batch == 0


def test_forced_ingest_gets_fresh_extraction_budget_each_operation():
    revenue = RevenueExecutionSpine()
    reasoner = _FakeReasoner()
    connector = _SequencedConnector()
    svc = IngestService(
        inbox=_Inbox(), connectors=[connector], revenue=revenue,
        entity_extractor=reasoner, max_extractions_per_batch=1,
    )
    svc.register_rss(source_key="demo", url="https://example.com/feed.xml")

    first = svc.ingest_source("demo")
    assert first.items[0].revenue_action_id is not None
    assert reasoner.calls == 1

    second = svc.ingest_source("demo")
    assert second.items[0].revenue_action_id is not None
    assert reasoner.calls == 2


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

    assert svc._maybe_queue_revenue_action(source, _rfp_item()) is None
    events = [e for e in store.read_all() if e.event_type == "revenue.signal_scored"]
    assert len(events) == 1
    assert events[0].payload["actionable"] is False


def test_extractor_not_called_when_signal_already_actionable():
    revenue = RevenueExecutionSpine()
    svc = IngestService(
        connectors=[RssConnector()], revenue=revenue, entity_extractor=_NeverCalledReasoner(),
    )
    source = svc.register_rss(source_key="demo", url="https://example.com/feed.xml")
    item = _rfp_item()
    item.metadata.update({
        "named_buyer": "City Procurement Office",
        "decision_maker": "Procurement Director Jane Doe",
        "visible_pain": "current vendor contract is expiring",
        "urgency_reason": "Bid window closes in 10 days",
        "payment_path": "Vendor bid support retainer",
        "contact_channel": "procurement@example.gov",
    })
    assert svc._maybe_queue_revenue_action(source, item) is not None
