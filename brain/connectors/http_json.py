"""HTTP JSON API connector — pulls list payloads into observations."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .http_client import HttpClient, HttpClientError
from .protocol import (
    ConnectorKind,
    ConnectorSource,
    FetchResult,
    FetchStatus,
    RawObservationItem,
    utcnow,
)


def _hash_parts(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()


def _dig(data: Any, path: str) -> Any:
    if not path:
        return data
    cur = data
    for part in path.split("."):
        if not part:
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _as_str(value: Any, *, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)[:limit]
    else:
        text = str(value)[:limit]
    return text.strip()


class HttpJsonConnector:
    kind = ConnectorKind.HTTP_JSON

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def supports(self, source: ConnectorSource) -> bool:
        return source.kind in {ConnectorKind.HTTP_JSON, ConnectorKind.HTTP_TEXT}

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

        if source.kind == ConnectorKind.HTTP_TEXT:
            text = resp.body.decode("utf-8", errors="replace").strip()
            if not text:
                return FetchResult(
                    source_key=source.source_key,
                    status=FetchStatus.EMPTY,
                    http_status=resp.status,
                    retrieved_at=started,
                    bytes_read=len(resp.body),
                    duration_ms=resp.duration_ms,
                )
            item_id = _hash_parts(source.source_key, text[:200])
            item = RawObservationItem(
                title=source.name or source.source_key,
                content=text[:8000],
                claim=text[:160],
                source_url=resp.final_url,
                item_id=item_id,
                content_hash=_hash_parts(source.source_key, text),
                confidence=0.5,
                signal_hints=["http_text"],
            )
            return FetchResult(
                source_key=source.source_key,
                status=FetchStatus.SUCCESS,
                items=[item],
                http_status=resp.status,
                retrieved_at=started,
                bytes_read=len(resp.body),
                duration_ms=resp.duration_ms,
            )

        try:
            payload = json.loads(resp.body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            return FetchResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED,
                error=f"json_decode:{exc}",
                http_status=resp.status,
                retrieved_at=started,
                bytes_read=len(resp.body),
                duration_ms=resp.duration_ms,
            )

        raw_items = _dig(payload, source.json_items_path) if source.json_items_path else payload
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        if not isinstance(raw_items, list):
            return FetchResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED,
                error="json_items_not_a_list",
                http_status=resp.status,
                retrieved_at=started,
                bytes_read=len(resp.body),
                duration_ms=resp.duration_ms,
                metadata={"path": source.json_items_path},
            )

        items: list[RawObservationItem] = []
        for row in raw_items[: max(1, source.max_items_per_fetch)]:
            if not isinstance(row, dict):
                continue
            title = _as_str(row.get(source.json_title_field) or row.get("title") or row.get("name"), limit=240)
            body = _as_str(
                row.get(source.json_body_field)
                or row.get("body")
                or row.get("summary")
                or row.get("description")
                or row.get("content"),
                limit=6000,
            )
            url = _as_str(row.get(source.json_url_field) or row.get("url") or row.get("link") or source.url, limit=2000)
            item_id = _as_str(
                row.get(source.json_id_field) or row.get("id") or row.get("guid") or url or title,
                limit=500,
            )
            if not title and not body:
                continue
            claim = title or body[:160]
            content = f"{title}\n\n{body}".strip() if title and body else (title or body)
            items.append(
                RawObservationItem(
                    title=title or claim[:120],
                    content=content,
                    claim=claim,
                    source_url=url or source.url,
                    item_id=item_id,
                    content_hash=_hash_parts(source.source_key, item_id, content),
                    confidence=0.55,
                    signal_hints=["http_json"],
                    metadata={"fields": list(row.keys())[:20]},
                )
            )

        status = FetchStatus.SUCCESS if items else FetchStatus.EMPTY
        return FetchResult(
            source_key=source.source_key,
            status=status,
            items=items,
            http_status=resp.status,
            retrieved_at=started,
            bytes_read=len(resp.body),
            duration_ms=resp.duration_ms,
        )
