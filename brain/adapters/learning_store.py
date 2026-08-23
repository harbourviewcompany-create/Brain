from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from uuid import UUID

try:
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:
    dict_row = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc,assignment]

from ..attribution import AttributionRecord, LearningResult
from ..domain import Edge, utcnow
from ..prediction import Prediction, PredictionStatus


def _json(value: Any) -> Any:
    return Jsonb(value) if Jsonb is not None else value


@dataclass
class InMemoryLearningStore:
    predictions: dict[UUID, Prediction] = field(default_factory=dict)
    edges: dict[UUID, Edge] = field(default_factory=dict)
    attributions: list[AttributionRecord] = field(default_factory=list)
    source_scores: dict[str, float] = field(default_factory=dict)

    def save(self, prediction: Prediction) -> None:
        self.predictions[prediction.id] = prediction

    def get(self, prediction_id: UUID) -> Prediction | None:
        return self.predictions.get(prediction_id)

    def get_edge(self, edge_id: UUID) -> Edge | None:
        return self.edges.get(edge_id)

    def upsert_edge(self, edge: Edge) -> None:
        self.edges[edge.id] = edge

    def delete_edge(self, edge_id: UUID) -> None:
        self.edges.pop(edge_id, None)

    def save_attribution(self, result: LearningResult) -> None:
        self.attributions.append(result.attribution)

    def apply_reliability_delta(self, source_key: str, delta: float) -> None:
        current = self.source_scores.get(source_key, 0.5)
        self.source_scores[source_key] = max(0.0, min(1.0, current + delta))


class PostgresPredictionStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def save(self, prediction: Prediction) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.predictions (
                    id, statement, expected_value, confidence, horizon_seconds,
                    belief_id, action_id, edge_ids, source_keys, status,
                    created_at, resolve_by, resolved_at, metadata
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                    statement = excluded.statement,
                    expected_value = excluded.expected_value,
                    confidence = excluded.confidence,
                    horizon_seconds = excluded.horizon_seconds,
                    belief_id = excluded.belief_id,
                    action_id = excluded.action_id,
                    edge_ids = excluded.edge_ids,
                    source_keys = excluded.source_keys,
                    status = excluded.status,
                    resolve_by = excluded.resolve_by,
                    resolved_at = excluded.resolved_at,
                    metadata = excluded.metadata
                """,
                (
                    prediction.id,
                    prediction.statement,
                    prediction.expected_value,
                    prediction.confidence,
                    int(prediction.horizon.total_seconds()),
                    prediction.belief_id,
                    prediction.action_id,
                    list(prediction.edge_ids),
                    list(prediction.source_keys),
                    str(prediction.status),
                    prediction.created_at,
                    prediction.resolve_by,
                    prediction.resolved_at,
                    _json(dict(prediction.metadata)),
                ),
            )
            conn.commit()

    def get(self, prediction_id: UUID) -> Prediction | None:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    select id, statement, expected_value, confidence, horizon_seconds,
                           belief_id, action_id, edge_ids, source_keys, status,
                           created_at, resolve_by, resolved_at, metadata
                    from public.predictions where id = %s
                    """,
                    (prediction_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return Prediction(
                    id=row["id"],
                    statement=row["statement"],
                    expected_value=float(row["expected_value"]),
                    confidence=float(row["confidence"]),
                    horizon=timedelta(seconds=int(row["horizon_seconds"])),
                    belief_id=row["belief_id"],
                    action_id=row["action_id"],
                    edge_ids=list(row["edge_ids"] or []),
                    source_keys=list(row["source_keys"] or []),
                    status=PredictionStatus(row["status"]),
                    created_at=row["created_at"],
                    resolve_by=row["resolve_by"],
                    resolved_at=row["resolved_at"],
                    metadata=dict(row["metadata"] or {}),
                )


class PostgresEdgeStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def get_edge(self, edge_id: UUID) -> Edge | None:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    select id, source_id, target_id, relation, weight, confidence,
                           evidence_ids, updated_at
                    from public.graph_edges where id = %s
                    """,
                    (edge_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return Edge(
                    id=row["id"],
                    source=row["source_id"],
                    target=row["target_id"],
                    relation=row["relation"],
                    weight=float(row["weight"]),
                    confidence=float(row["confidence"]),
                    evidence_ids=set(row["evidence_ids"] or []),
                    updated_at=row["updated_at"],
                )

    def upsert_edge(self, edge: Edge) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.graph_edges (
                    id, source_id, target_id, relation, weight, confidence, evidence_ids, updated_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                    weight = excluded.weight,
                    confidence = excluded.confidence,
                    evidence_ids = excluded.evidence_ids,
                    updated_at = excluded.updated_at
                """,
                (
                    edge.id,
                    edge.source,
                    edge.target,
                    edge.relation,
                    edge.weight,
                    edge.confidence,
                    list(edge.evidence_ids),
                    edge.updated_at or utcnow(),
                ),
            )
            conn.commit()

    def delete_edge(self, edge_id: UUID) -> None:
        with self.pool.connection() as conn:
            conn.execute("delete from public.graph_edges where id = %s", (edge_id,))
            conn.commit()


class PostgresAttributionStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def save_attribution(self, result: LearningResult) -> None:
        attr = result.attribution
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.attribution_records (
                    id, outcome_id, prediction_id, edge_ids, source_keys,
                    reward_score, prediction_error, edge_deltas, source_deltas,
                    rationale, created_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    attr.id,
                    attr.outcome_id,
                    attr.prediction_id,
                    list(attr.edge_ids),
                    list(attr.source_keys),
                    attr.reward_score,
                    attr.prediction_error,
                    _json(dict(attr.edge_deltas)),
                    _json(dict(attr.source_deltas)),
                    _json(list(attr.rationale)),
                    attr.created_at,
                ),
            )
            conn.commit()


class PostgresSourceStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def apply_reliability_delta(self, source_key: str, delta: float) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                update public.sources
                set authority_score = greatest(0.0, least(1.0, authority_score + %s)),
                    historical_utility = greatest(0.0, least(1.0, historical_utility + %s))
                where key = %s
                """,
                (delta, delta * 0.5, source_key),
            )
            conn.commit()
