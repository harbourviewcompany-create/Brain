"""RSS 2.0 and Atom feed connector — stdlib XML parser."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .http_client import HttpClient, HttpClientError
from .protocol import (
    ConnectorKind,
    ConnectorSource,
    FetchResult,
    FetchStatus,
    RawObservationItem,
    utcnow,
)

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").replace("&nbsp;", " ").strip()


def _clean(text: str, *, limit: int = 4000) -> str:
    t = _strip_html(text)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def _hash_parts(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()


def _parse_date(value: str | None) -> datetime:
    if not value:
        return utcnow()
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        iso = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return utcnow()


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


class RssConnector:
    kind = ConnectorKind.RSS

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def supports(self, source: ConnectorSource) -> bool:
        return source.kind in {ConnectorKind.RSS, ConnectorKind.ATOM}

    def fetch(self, source: ConnectorSource) -> FetchResult:
        started = utcnow()
        try:
            resp = self.client.get(
                source.url,
                headers=source.headers,
                timeout=source.timeout_seconds,
            )
        except HttpClientError as exc:
            return FetchResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED,
                error=str(exc),
                http_status=exc.status,
                retrieved_at=started,
            )

        try:
            text = resp.body.decode("utf-8", errors="replace")
            items = self._parse_feed(text, source=source, final_url=resp.final_url)
        except ET.ParseError as exc:
            return FetchResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED,
                error=f"xml_parse_error:{exc}",
                http_status=resp.status,
                retrieved_at=started,
                bytes_read=len(resp.body),
                duration_ms=resp.duration_ms,
            )
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED,
                error=f"parse_error:{exc!r}",
                http_status=resp.status,
                retrieved_at=started,
                bytes_read=len(resp.body),
                duration_ms=resp.duration_ms,
            )

        limit = max(1, source.max_items_per_fetch)
        items = items[:limit]
        status = FetchStatus.SUCCESS if items else FetchStatus.EMPTY
        return FetchResult(
            source_key=source.source_key,
            status=status,
            items=items,
            http_status=resp.status,
            retrieved_at=started,
            bytes_read=len(resp.body),
            duration_ms=resp.duration_ms,
            metadata={"final_url": resp.final_url, "format": self._detect_format(text)},
        )

    def _detect_format(self, text: str) -> str:
        head = text.lstrip()[:200].lower()
        if "<feed" in head and "atom" in head:
            return "atom"
        if "<rss" in head:
            return "rss"
        return "xml"

    def _parse_feed(self, text: str, *, source: ConnectorSource, final_url: str):
        root = ET.fromstring(text)
        root_tag = _local(root.tag).lower()
        if root_tag == "feed":
            return self._parse_atom(root, source=source, final_url=final_url)
        channel = root.find("channel")
        if channel is None:
            for child in root:
                if _local(child.tag).lower() == "channel":
                    channel = child
                    break
        if channel is None:
            return self._parse_atom(root, source=source, final_url=final_url)
        return self._parse_rss_channel(channel, source=source, final_url=final_url)

    def _parse_rss_channel(self, channel, *, source: ConnectorSource, final_url: str):
        items = []
        for node in channel:
            if _local(node.tag).lower() != "item":
                continue
            title = _clean(self._child_text(node, "title") or "")
            link = self._child_text(node, "link") or final_url
            guid = self._child_text(node, "guid") or link or title
            description = _clean(
                self._child_text(node, "description")
                or self._child_text(node, "content:encoded")
                or ""
            )
            pub = _parse_date(self._child_text(node, "pubDate") or self._child_text(node, "date"))
            body = description or title
            if not title and not body:
                continue
            claim = title or body[:160]
            content = f"{title}\n\n{body}".strip() if title and body else (title or body)
            items.append(
                RawObservationItem(
                    title=title or claim[:120],
                    content=content,
                    claim=claim,
                    source_url=link,
                    item_id=guid,
                    content_hash=_hash_parts(source.source_key, guid, content),
                    observed_at=pub,
                    confidence=0.6,
                    signal_hints=["rss"],
                    metadata={"format": "rss", "feed_url": source.url},
                )
            )
        return items

    def _parse_atom(self, root, *, source: ConnectorSource, final_url: str):
        items = []
        entries = [c for c in root if _local(c.tag).lower() == "entry"]
        if not entries:
            entries = list(root.findall("atom:entry", _ATOM_NS))
        for entry in entries:
            title = _clean(self._child_text(entry, "title") or "")
            link = self._atom_link(entry) or final_url
            entry_id = self._child_text(entry, "id") or link or title
            summary = _clean(
                self._child_text(entry, "summary")
                or self._child_text(entry, "content")
                or ""
            )
            pub = _parse_date(
                self._child_text(entry, "updated")
                or self._child_text(entry, "published")
            )
            body = summary or title
            if not title and not body:
                continue
            claim = title or body[:160]
            content = f"{title}\n\n{body}".strip() if title and body else (title or body)
            items.append(
                RawObservationItem(
                    title=title or claim[:120],
                    content=content,
                    claim=claim,
                    source_url=link,
                    item_id=entry_id,
                    content_hash=_hash_parts(source.source_key, entry_id, content),
                    observed_at=pub,
                    confidence=0.6,
                    signal_hints=["atom"],
                    metadata={"format": "atom", "feed_url": source.url},
                )
            )
        return items

    def _child_text(self, parent, name: str):
        name_l = name.lower()
        for child in parent:
            local = _local(child.tag).lower()
            if local == name_l or local.endswith(":" + name_l) or local == name_l.split(":")[-1]:
                text = "".join(child.itertext()).strip()
                if text:
                    return text
        return None

    def _atom_link(self, entry):
        for child in entry:
            if _local(child.tag).lower() != "link":
                continue
            rel = (child.attrib.get("rel") or "alternate").lower()
            href = child.attrib.get("href")
            if href and rel in {"alternate", ""}:
                return href
        for child in entry:
            if _local(child.tag).lower() == "link" and child.attrib.get("href"):
                return child.attrib.get("href")
        return None
