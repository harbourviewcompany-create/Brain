from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import mean
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class BenchmarkMetric:
    name: str
    value: float
    higher_is_better: bool = True
    weight: float = 1.0
    evidence_refs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    capability: str
    expected: float | bool | str
    observed: float | bool | str
    confidence: float | None = None
    latency_ms: float = 0.0
    cost: float = 0.0
    evidence_refs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BenchmarkResult:
    suite_id: str
    metrics: list[BenchmarkMetric]
    score: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class BenchmarkBaseline:
    suite_id: str
    result_id: UUID
    score: float
    metric_values: dict[str, float]
    commit_sha: str
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RegressionDecision:
    candidate_result_id: UUID
    baseline_id: UUID
    passed: bool
    regressions: list[str]
    improvements: list[str]
    score_delta: float
    id: UUID = field(default_factory=uuid4)


class CognitiveBenchmarkLab:
    """Deterministic evaluation layer for cognitive changes and self-modification."""

    @staticmethod
    def brier_score(cases: list[BenchmarkCase]) -> BenchmarkMetric:
        binary = [case for case in cases if isinstance(case.expected, bool) and case.confidence is not None]
        if not binary:
            return BenchmarkMetric("brier_accuracy", 0.0, True, 1.0, [])
        losses = []
        refs: set[str] = set()
        for case in binary:
            target = 1.0 if case.expected else 0.0
            probability = _clamp01(case.confidence or 0.0)
            losses.append((probability - target) ** 2)
            refs.update(case.evidence_refs)
        return BenchmarkMetric("brier_accuracy", 1.0 - mean(losses), True, 1.5, sorted(refs))

    @staticmethod
    def exact_accuracy(cases: list[BenchmarkCase]) -> BenchmarkMetric:
        if not cases:
            return BenchmarkMetric("exact_accuracy", 0.0)
        hits = sum(1 for case in cases if case.observed == case.expected)
        refs = sorted({ref for case in cases for ref in case.evidence_refs})
        return BenchmarkMetric("exact_accuracy", hits / len(cases), True, 1.0, refs)

    @staticmethod
    def latency_efficiency(cases: list[BenchmarkCase], *, target_ms: float = 1000.0) -> BenchmarkMetric:
        if not cases:
            return BenchmarkMetric("latency_efficiency", 0.0)
        avg = mean(max(case.latency_ms, 0.0) for case in cases)
        value = 1.0 / (1.0 + avg / max(target_ms, 1.0))
        return BenchmarkMetric("latency_efficiency", value, True, 0.5)

    @staticmethod
    def cost_efficiency(cases: list[BenchmarkCase], *, target_cost: float = 1.0) -> BenchmarkMetric:
        if not cases:
            return BenchmarkMetric("cost_efficiency", 0.0)
        avg = mean(max(case.cost, 0.0) for case in cases)
        value = 1.0 / (1.0 + avg / max(target_cost, 1e-9))
        return BenchmarkMetric("cost_efficiency", value, True, 0.5)

    def evaluate(self, suite_id: str, cases: list[BenchmarkCase]) -> BenchmarkResult:
        if not cases:
            raise ValueError("benchmark suite requires cases")
        if any(not case.evidence_refs for case in cases):
            raise ValueError("benchmark cases require evidence")
        metrics = [
            self.exact_accuracy(cases),
            self.brier_score(cases),
            self.latency_efficiency(cases),
            self.cost_efficiency(cases),
        ]
        weighted = sum(_clamp01(metric.value) * metric.weight for metric in metrics)
        total_weight = sum(metric.weight for metric in metrics)
        return BenchmarkResult(
            suite_id=suite_id,
            metrics=metrics,
            score=weighted / total_weight,
            evidence_refs=sorted({ref for case in cases for ref in case.evidence_refs}),
        )

    @staticmethod
    def baseline(result: BenchmarkResult, *, commit_sha: str) -> BenchmarkBaseline:
        if not commit_sha:
            raise ValueError("benchmark baseline requires commit sha")
        return BenchmarkBaseline(
            suite_id=result.suite_id,
            result_id=result.id,
            score=result.score,
            metric_values={metric.name: metric.value for metric in result.metrics},
            commit_sha=commit_sha,
        )

    @staticmethod
    def compare(
        candidate: BenchmarkResult,
        baseline: BenchmarkBaseline,
        *,
        max_metric_regression: float = 0.02,
        max_total_regression: float = 0.01,
    ) -> RegressionDecision:
        if candidate.suite_id != baseline.suite_id:
            raise ValueError("benchmark suite mismatch")
        regressions: list[str] = []
        improvements: list[str] = []
        for metric in candidate.metrics:
            if metric.name not in baseline.metric_values:
                continue
            delta = metric.value - baseline.metric_values[metric.name]
            if delta < -max_metric_regression:
                regressions.append(f"{metric.name}:{delta:.4f}")
            elif delta > max_metric_regression:
                improvements.append(f"{metric.name}:{delta:.4f}")
        score_delta = candidate.score - baseline.score
        if score_delta < -max_total_regression:
            regressions.append(f"total_score:{score_delta:.4f}")
        return RegressionDecision(
            candidate_result_id=candidate.id,
            baseline_id=baseline.id,
            passed=not regressions,
            regressions=regressions,
            improvements=improvements,
            score_delta=score_delta,
        )
