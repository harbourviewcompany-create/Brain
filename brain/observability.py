from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .domain import utcnow


@dataclass(slots=True)
class CognitiveSpan:
    name: str
    category: str
    attributes: dict[str, str | int | float | bool]
    trace_id: UUID
    parent_span_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=utcnow)
    ended_at: datetime | None = None
    status: str = "open"

    def finish(self, status: str = "ok") -> "CognitiveSpan":
        self.status = status
        self.ended_at = utcnow()
        return self


@dataclass(slots=True)
class CognitiveMetric:
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=utcnow)


class CognitiveTelemetry:
    """Provider-neutral telemetry that can be exported to OpenTelemetry collectors."""

    def __init__(self, *, max_spans: int = 5000, max_metrics: int = 5000) -> None:
        self.max_spans = max_spans
        self.max_metrics = max_metrics
        self.spans: list[CognitiveSpan] = []
        self.metrics: list[CognitiveMetric] = []

    def start_span(
        self,
        name: str,
        category: str,
        *,
        trace_id: UUID | None = None,
        parent_span_id: UUID | None = None,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> CognitiveSpan:
        span = CognitiveSpan(
            name=name,
            category=category,
            attributes=dict(attributes or {}),
            trace_id=trace_id or uuid4(),
            parent_span_id=parent_span_id,
        )
        self.spans.append(span)
        if len(self.spans) > self.max_spans:
            del self.spans[: len(self.spans) - self.max_spans]
        return span

    def metric(self, name: str, value: float, **labels: str) -> CognitiveMetric:
        metric = CognitiveMetric(name, float(value), dict(labels))
        self.metrics.append(metric)
        if len(self.metrics) > self.max_metrics:
            del self.metrics[: len(self.metrics) - self.max_metrics]
        return metric

    def snapshot(self) -> dict:
        return {
            "spans": [self._serialize_span(span) for span in self.spans],
            "metrics": [self._serialize_metric(metric) for metric in self.metrics],
        }

    def json_lines(self) -> str:
        records = [
            {"record_type": "span", **self._serialize_span(span)} for span in self.spans
        ] + [
            {"record_type": "metric", **self._serialize_metric(metric)} for metric in self.metrics
        ]
        return "\n".join(json.dumps(record, sort_keys=True) for record in records)

    @staticmethod
    def _serialize_span(span: CognitiveSpan) -> dict:
        raw = asdict(span)
        raw["id"] = str(span.id)
        raw["trace_id"] = str(span.trace_id)
        raw["parent_span_id"] = str(span.parent_span_id) if span.parent_span_id else None
        raw["started_at"] = span.started_at.isoformat()
        raw["ended_at"] = span.ended_at.isoformat() if span.ended_at else None
        return raw

    @staticmethod
    def _serialize_metric(metric: CognitiveMetric) -> dict:
        raw = asdict(metric)
        raw["recorded_at"] = metric.recorded_at.isoformat()
        return raw
