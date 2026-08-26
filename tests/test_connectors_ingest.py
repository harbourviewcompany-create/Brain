"""Connector protocol, RSS/HTTP fetchers, and ingest_due_sources pipeline."""

from __future__ import annotations

from datetime import timedelta

import pytest

from brain.connectors.http_client import HttpClient, HttpClientError, HttpResponse
from brain.connectors.http_json import HttpJsonConnector
from brain.connectors.protocol import (
    AccessDisposition,
    ConnectorKind,
    ConnectorSource,
    FetchStatus,
    utcnow,
)
from brain.connectors.rss import RssConnector
from brain.connectors.service import IngestService
from brain.connectors.store import InMemoryConnectorRegistry
from brain.memory import InMemoryBrainStore
from brain.sensory_inbox import InMemorySensoryInbox

SAMPLE_RSS = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\">
  <channel>
    <title>Example Feed</title>
    <link>https://example.com/</link>
    <item>
      <title>Alpha Signal Detected</title>
      <link>https://example.com/a</link>
      <guid>https://example.com/a</guid>
      <pubDate>Mon, 25 Aug 2026 10:00:00 GMT</pubDate>
      <description>Markets expanded in region north with elevated hiring.</description>
    </item>
    <item>
      <title>Beta Event</title>
      <link>https://example.com/b</link>
      <guid>guid-beta</guid>
      <description>Regulatory portal updated licensing requirements.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM = """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<feed xmlns=\"http://www.w3.org/2005/Atom\">
  <title>Atom Example</title>
  <entry>
    <title>Atom Entry One</title>
    <id>urn:test:1</id>
    <link href=\"https://example.com/atom/1\" rel=\"alternate\"/>
    <updated>2026-08-25T12:00:00Z</updated>
    <summary>Summary of atom entry one about supply constraints.</summary>
  </entry>
</feed>
"""

SAMPLE_JSON = {
    "items": [
        {
            "id": "j1",
            "title": "JSON Headline",
            "body": "Structured API payload describing capital raise activity.",
            "url": "https://example.com/j1",
        },
        {
            "id": "j2",
            "title": "Second JSON",
            "summary": "Another observation from the API.",
            "link": "https://example.com/j2",
        },
    ]
}


class FakeHttpClient:
    def __init__(self, mapping: dict[str, HttpResponse | Exception]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def get(self, url: str, *, headers=None, timeout=None) -> HttpResponse:
        self.calls.append(url)
        value = self.mapping.get(url)
        if value is None:
            raise HttpClientError(f"unexpected_url:{url}")
        if isinstance(value, Exception):
            raise value
        return value


def _resp(url: str, body: str | bytes, status: int = 200) -> HttpResponse:
    raw = body.encode("utf-8") if isinstance(body, str) else body
    return HttpResponse(
        url=url,
        status=status,
        body=raw,
        headers={"content-type": "application/xml"},
        duration_ms=12.0,
        final_url=url,
    )


def test_rss_connector_parses_items():
    url = "https://example.com/feed.xml"
    client = FakeHttpClient({url: _resp(url, SAMPLE_RSS)})
    conn = RssConnector(client=client)  # type: ignore[arg-type]
    source = ConnectorSource(source_key="ex-rss", url=url, kind=ConnectorKind.RSS)
    result = conn.fetch(source)
    assert result.status == FetchStatus.SUCCESS
    assert len(result.items) == 2
    assert result.items[0].title == "Alpha Signal Detected"
    assert "hiring" in result.items[0].content.lower()
    assert result.items[0].content_hash
    assert result.items[0].source_url.endswith("/a")


def test_atom_connector_parses_entries():
    url = "https://example.com/atom.xml"
    client = FakeHttpClient({url: _resp(url, SAMPLE_ATOM)})
    conn = RssConnector(client=client)  # type: ignore[arg-type]
    source = ConnectorSource(source_key="ex-atom", url=url, kind=ConnectorKind.ATOM)
    result = conn.fetch(source)
    assert result.status == FetchStatus.SUCCESS
    assert len(result.items) == 1
    assert result.items[0].title == "Atom Entry One"
    assert "supply" in result.items[0].content.lower()


def test_http_json_connector_parses_list():
    import json

    url = "https://api.example.com/signals"
    body = json.dumps(SAMPLE_JSON)
    client = FakeHttpClient({url: _resp(url, body)})
    conn = HttpJsonConnector(client=client)  # type: ignore[arg-type]
    source = ConnectorSource(
        source_key="ex-json",
        url=url,
        kind=ConnectorKind.HTTP_JSON,
        json_items_path="items",
        json_title_field="title",
        json_body_field="body",
        json_url_field="url",
        json_id_field="id",
    )
    result = conn.fetch(source)
    assert result.status == FetchStatus.SUCCESS
    assert len(result.items) == 2
    assert result.items[0].title == "JSON Headline"


def test_prohibited_source_not_due_and_forced_skip():
    inbox = InMemorySensoryInbox()
    svc = IngestService(inbox=inbox)
    svc.register_source(
        ConnectorSource(
            source_key="bad",
            url="https://example.com/x",
            kind=ConnectorKind.RSS,
            access=AccessDisposition.PROHIBITED,
            enabled=True,
        )
    )
    src = svc.registry.get("bad")
    assert src is not None
    assert src.enabled is False
    assert src.is_due() is False
    batch = svc.ingest_due_sources()
    assert batch.sources_due == 0
    forced = svc.ingest_source("bad")
    assert forced.status == FetchStatus.SKIPPED.value


def test_ingest_due_sources_enqueues_and_dedupes():
    url = "https://example.com/feed.xml"
    client = FakeHttpClient({url: _resp(url, SAMPLE_RSS)})
    inbox = InMemorySensoryInbox()
    store = InMemoryBrainStore()
    registry = InMemoryConnectorRegistry()
    svc = IngestService(
        registry=registry,
        inbox=inbox,
        event_store=store,
        connectors=[RssConnector(client=client)],  # type: ignore[list-item]
    )
    svc.register_rss(source_key="demo", url=url, refresh_seconds=60)
    src = svc.registry.get("demo")
    assert src is not None
    src.next_due_at = utcnow() - timedelta(seconds=5)

    batch1 = svc.ingest_due_sources()
    assert batch1.observations_enqueued == 2
    assert inbox.stats()["pending"] == 2

    src.next_due_at = utcnow() - timedelta(seconds=1)
    batch2 = svc.ingest_due_sources()
    assert batch2.observations_enqueued == 0
    assert batch2.observations_deduped == 2
    assert inbox.stats()["pending"] == 2

    events = store.read_all()
    assert any(e.event_type == "ingest.fetch_completed" for e in events)
    assert any(e.event_type == "ingest.batch_completed" for e in events)


def test_ingest_feeds_cognition_path():
    url = "https://example.com/feed.xml"
    client = FakeHttpClient({url: _resp(url, SAMPLE_RSS)})
    from brain.heartbeat import build_default_heartbeat

    hb = build_default_heartbeat(with_learning=True)
    hb.bootstrap_mind()
    svc = IngestService(
        inbox=hb.inbox,
        event_store=hb.event_store,
        connectors=[RssConnector(client=client)],  # type: ignore[list-item]
    )
    svc.register_rss(source_key="live-rss", url=url, refresh_seconds=30)
    svc.registry.get("live-rss").next_due_at = utcnow() - timedelta(seconds=1)  # type: ignore[union-attr]
    batch = svc.ingest_due_sources()
    assert batch.observations_enqueued >= 1
    assert hb.inbox.stats()["pending"] >= 1
    snap = hb.tick(max_items=3)
    assert snap["total_processed"] >= 1


def test_backoff_on_failure():
    url = "https://example.com/down.xml"
    client = FakeHttpClient({url: HttpClientError("http_error:500", status=500)})
    registry = InMemoryConnectorRegistry()
    svc = IngestService(
        registry=registry,
        inbox=InMemorySensoryInbox(),
        connectors=[RssConnector(client=client)],  # type: ignore[list-item]
    )
    svc.register_rss(source_key="down", url=url, refresh_seconds=60)
    src = svc.registry.get("down")
    assert src is not None
    src.next_due_at = utcnow() - timedelta(seconds=1)
    before = src.next_due_at
    batch = svc.ingest_due_sources()
    assert batch.failures == 1
    assert src.consecutive_failures == 1
    assert src.next_due_at > before


def test_http_client_rejects_non_http():
    client = HttpClient()
    with pytest.raises(HttpClientError):
        client.get("ftp://example.com/x")
