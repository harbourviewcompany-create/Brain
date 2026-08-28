from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from ..attribution import LearningResult
from ..domain import Edge, utcnow
from ..prediction import Prediction, PredictionStatus
from .turso import TursoDatabase, _dt, _iso, _json_dumps, _json_loads, _uuid


class TursoPredictionStore:
    def __init__(self, db: TursoDatabase) -> None:
        self.db = db

    def save(self, prediction: Prediction) -> None:
        self.db.execute(
            """
            INSERT INTO predictions(
                id,statement,expected_value,confidence,horizon_seconds,belief_id,action_id,
                edge_ids,source_keys,status,created_at,resolve_by,resolved_at,metadata
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET statement=excluded.statement,
                expected_value=excluded.expected_value,confidence=excluded.confidence,
                horizon_seconds=excluded.horizon_seconds,belief_id=excluded.belief_id,
                action_id=excluded.action_id,edge_ids=excluded.edge_ids,
                source_keys=excluded.source_keys,status=excluded.status,
                resolve_by=excluded.resolve_by,resolved_at=excluded.resolved_at,
                metadata=excluded.metadata
            """,
            (
                str(prediction.id),
                prediction.statement,
                prediction.expected_value,
                prediction.confidence,
                int(prediction.horizon.total_seconds()),
                str(prediction.belief_id) if prediction.belief_id else None,
                str(prediction.action_id) if prediction.action_id else None,
                _json_dumps(list(prediction.edge_ids)),
                _json_dumps(list(prediction.source_keys)),
                str(prediction.status),
                _iso(prediction.created_at),
                _iso(prediction.resolve_by) if prediction.resolve_by else None,
                _iso(prediction.resolved_at) if prediction.resolved_at else None,
                _json_dumps(dict(prediction.metadata)),
            ),
        )
        self.db.commit()

    @staticmethod
    def _row_to_prediction(row) -> Prediction:
        return Prediction(
            id=UUID(str(row["id"])),
            statement=str(row["statement"]),
            expected_value=float(row["expected_value"]),
            confidence=float(row["confidence"]),
            horizon=timedelta(seconds=int(row["horizon_seconds"])),
            belief_id=_uuid(row.get("belief_id")),
            action_id=_uuid(row.get("action_id")),
            edge_ids=[UUID(str(value)) for value in _json_loads(row.get("edge_ids"), [])],
            source_keys=list(_json_loads(row.get("source_keys"), [])),
            status=PredictionStatus(str(row["status"])),
            created_at=_dt(row["created_at"]),
            resolve_by=_dt(row["resolve_by"]) if row.get("resolve_by") else None,
            resolved_at=_dt(row["resolved_at"]) if row.get("resolved_at") else None,
            metadata=dict(_json_loads(row.get("metadata"), {})),
        )

    def get(self, prediction_id: UUID) -> Prediction | None:
        row = self.db.fetchone(
            "SELECT * FROM predictions WHERE id=?",
            (str(prediction_id),),
        )
        return self._row_to_prediction(row) if row else None

    def list_open(self) -> list[Prediction]:
        rows = self.db.fetchall("SELECT * FROM predictions WHERE status='open'")
        return [self._row_to_prediction(row) for row in rows]


class TursoEdgeStore:
    def __init__(self, db: TursoDatabase) -> None:
        self.db = db

    @staticmethod
    def _row_to_edge(row) -> Edge:
        return Edge(
            id=UUID(str(row["id"])),
            source=UUID(str(row["source_id"])),
            target=UUID(str(row["target_id"])),
            relation=str(row["relation"]),
            weight=float(row["weight"]),
            confidence=float(row["confidence"]),
            evidence_ids={UUID(str(value)) for value in _json_loads(row.get("evidence_ids"), [])},
            updated_at=_dt(row["updated_at"]),
        )

    def get_edge(self, edge_id: UUID) -> Edge | None:
        row = self.db.fetchone("SELECT * FROM graph_edges WHERE id=?", (str(edge_id),))
        return self._row_to_edge(row) if row else None

    def list_edges(self) -> list[Edge]:
        rows = self.db.fetchall("SELECT * FROM graph_edges ORDER BY updated_at DESC,id")
        return [self._row_to_edge(row) for row in rows]

    def upsert_edge(self, edge: Edge) -> None:
        updated_at = edge.updated_at or utcnow()
        self.db.execute(
            """
            INSERT INTO graph_edges(id,source_id,target_id,relation,weight,confidence,evidence_ids,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET weight=excluded.weight,
                confidence=excluded.confidence,evidence_ids=excluded.evidence_ids,
                updated_at=excluded.updated_at
            """,
            (
                str(edge.id),
                str(edge.source),
                str(edge.target),
                edge.relation,
                edge.weight,
                edge.confidence,
                _json_dumps(list(edge.evidence_ids)),
                _iso(updated_at),
            ),
        )
        self.db.commit()

    def delete_edge(self, edge_id: UUID) -> None:
        self.db.execute("DELETE FROM graph_edges WHERE id=?", (str(edge_id),))
        self.db.commit()


class TursoAttributionStore:
    def __init__(self, db: TursoDatabase) -> None:
        self.db = db

    def save_attribution(self, result: LearningResult) -> None:
        attr = result.attribution
        self.db.execute(
            """
            INSERT OR IGNORE INTO attribution_records(
                id,outcome_id,prediction_id,edge_ids,source_keys,reward_score,
                prediction_error,edge_deltas,source_deltas,rationale,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                str(attr.id),
                str(attr.outcome_id),
                str(attr.prediction_id) if attr.prediction_id else None,
                _json_dumps(list(attr.edge_ids)),
                _json_dumps(list(attr.source_keys)),
                attr.reward_score,
                attr.prediction_error,
                _json_dumps(dict(attr.edge_deltas)),
                _json_dumps(dict(attr.source_deltas)),
                _json_dumps(list(attr.rationale)),
                _iso(attr.created_at),
            ),
        )
        self.db.commit()


class TursoSourceStore:
    def __init__(self, db: TursoDatabase) -> None:
        self.db = db

    def apply_reliability_delta(self, source_key: str, delta: float) -> None:
        row = self.db.fetchone(
            "SELECT authority_score,historical_utility FROM sources WHERE key=?",
            (source_key,),
        )
        if not row:
            return
        authority = max(0.0, min(1.0, float(row["authority_score"]) + delta))
        utility = max(0.0, min(1.0, float(row["historical_utility"]) + delta * 0.5))
        self.db.execute(
            "UPDATE sources SET authority_score=?,historical_utility=? WHERE key=?",
            (authority, utility, source_key),
        )
        self.db.commit()
