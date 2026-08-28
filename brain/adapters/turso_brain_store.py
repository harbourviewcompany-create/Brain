from __future__ import annotations

import threading
import time
from typing import Any
from uuid import UUID

from ..beliefs import rebuild_fingerprints
from ..domain import Belief, BeliefState, Edge, Evidence, Node, RewireEvent, RewireOperation
from ..memory import InMemoryBrainStore
from ..prediction import Prediction
from .turso import (
    TursoDatabase,
    TursoEventStore,
    TursoProjectionCheckpointStore,
    _dt,
    _iso,
    _json_dumps,
    _json_loads,
    _uuid,
)


class TursoBrainStore(InMemoryBrainStore):
    """Write-through Brain state for stateless/serverless execution.

    The in-memory dictionaries remain disposable runtime projections. Turso is
    authoritative and hydrate() rebuilds them on cold start just as the legacy
    PostgresBrainStore does.
    """

    COGNITION_EVENT_TYPES = (
        "cycle.completed",
        "signal.enqueued",
        "observation.received",
        "belief.created",
        "belief.updated",
    )

    def __init__(
        self,
        database_url: str | None = None,
        auth_token: str | None = None,
        *,
        db: TursoDatabase | None = None,
    ) -> None:
        super().__init__()
        self._owns_db = db is None
        self.db = db or TursoDatabase(database_url, auth_token)
        self.event_store = TursoEventStore(self.db)
        self.checkpoint_store = TursoProjectionCheckpointStore(self.db)
        self._refresh_lock = threading.Lock()
        self.hydrate()
        self._hydrated_at: float | None = time.monotonic()

    def close(self) -> None:
        if self._owns_db:
            self.db.close()

    def database_healthy(self, *, timeout: float = 3.0) -> bool:
        del timeout  # network timeout belongs to the libSQL client transport
        try:
            row = self.db.connection.execute("SELECT 1").fetchone()
            return bool(row and int(row[0]) == 1)
        except Exception:
            return False

    def storage_health(self) -> dict[str, Any]:
        try:
            return self.event_store.health()
        except Exception as exc:
            return {"reachable": False, "error": type(exc).__name__}

    def hydrate(self) -> None:
        self.beliefs.clear()
        self.evidence.clear()
        self.nodes.clear()
        self.edges.clear()
        self.predictions.clear()
        self.rewires.clear()

        for row in self.db.fetchall(
            "SELECT id,statement,confidence,state,unknowns,version,updated_at FROM beliefs"
        ):
            belief = Belief(
                id=UUID(str(row["id"])),
                statement=str(row["statement"]),
                confidence=float(row["confidence"]),
                state=BeliefState(str(row["state"])),
                unknowns=list(_json_loads(row.get("unknowns"), [])),
                updated_at=_dt(row["updated_at"]),
                version=int(row["version"]),
            )
            self.beliefs[belief.id] = belief

        for row in self.db.fetchall(
            "SELECT id,observation_id,claim,reliability,created_at,metadata FROM evidence"
        ):
            metadata = dict(_json_loads(row.get("metadata"), {}))
            source_id = str(metadata.pop("source_id", "unknown"))
            evidence = Evidence(
                id=UUID(str(row["id"])),
                observation_id=_uuid(row.get("observation_id")),
                claim=str(row["claim"]),
                source_id=source_id,
                reliability=float(row["reliability"]),
                created_at=_dt(row["created_at"]),
                metadata=metadata,
            )
            self.evidence[evidence.id] = evidence

        for row in self.db.fetchall("SELECT belief_id,evidence_id,relation FROM belief_evidence"):
            belief = self.beliefs.get(UUID(str(row["belief_id"])))
            if belief is None:
                continue
            evidence_id = UUID(str(row["evidence_id"]))
            if str(row["relation"]) == "supports":
                belief.supporting_evidence.add(evidence_id)
            elif str(row["relation"]) == "contradicts":
                belief.contradicting_evidence.add(evidence_id)

        for belief in self.beliefs.values():
            rebuild_fingerprints(belief, self.evidence)

        for row in self.db.fetchall("SELECT id,kind,node_key,properties FROM graph_nodes"):
            node = Node(
                id=UUID(str(row["id"])),
                kind=str(row["kind"]),
                key=str(row["node_key"]),
                properties=dict(_json_loads(row.get("properties"), {})),
            )
            self.nodes[node.id] = node

        for row in self.db.fetchall(
            "SELECT id,source_id,target_id,relation,weight,confidence,evidence_ids,updated_at "
            "FROM graph_edges"
        ):
            edge = Edge(
                id=UUID(str(row["id"])),
                source=UUID(str(row["source_id"])),
                target=UUID(str(row["target_id"])),
                relation=str(row["relation"]),
                weight=float(row["weight"]),
                confidence=float(row["confidence"]),
                evidence_ids={UUID(str(value)) for value in _json_loads(row.get("evidence_ids"), [])},
                updated_at=_dt(row["updated_at"]),
            )
            self.edges[edge.id] = edge

        for row in self.db.fetchall(
            "SELECT id,operation,target_id,reason,previous,current,evidence_ids,created_at "
            "FROM rewire_events ORDER BY created_at,id"
        ):
            self.rewires.append(
                RewireEvent(
                    id=UUID(str(row["id"])),
                    operation=RewireOperation(str(row["operation"])),
                    target_id=UUID(str(row["target_id"])),
                    reason=str(row["reason"]),
                    previous=dict(_json_loads(row.get("previous"), {})),
                    current=dict(_json_loads(row.get("current"), {})),
                    evidence_ids=[UUID(str(value)) for value in _json_loads(row.get("evidence_ids"), [])],
                    created_at=_dt(row["created_at"]),
                )
            )

    def cognition_counters(self) -> dict[str, int]:
        return self.event_store.count_by_type(self.COGNITION_EVENT_TYPES)

    def refresh_if_stale(self, max_age_seconds: float) -> bool:
        if max_age_seconds < 0:
            return False
        now = time.monotonic()
        with self._refresh_lock:
            if self._hydrated_at is not None and now - self._hydrated_at < max_age_seconds:
                return False
            self._hydrated_at = now
        self.hydrate()
        return True

    def append(self, event) -> None:
        self.event_store.append(event)
        # Keep only process-local new events in the disposable list; canonical
        # replay/read operations always delegate to event_store.
        InMemoryBrainStore.append(self, event)

    def read_all(self, *, limit: int | None = None):
        return self.event_store.read_all(limit=limit)

    def read_recent(self, *, event_types, limit: int = 200):
        return self.event_store.read_recent(event_types=event_types, limit=limit)

    def read_after(self, occurred_at, event_id: UUID):
        return self.event_store.read_after(occurred_at, event_id)

    def save(self, item) -> None:
        if isinstance(item, Belief):
            self.db.execute(
                """
                INSERT INTO beliefs(id,statement,confidence,state,unknowns,version,updated_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET statement=excluded.statement,
                    confidence=excluded.confidence,state=excluded.state,
                    unknowns=excluded.unknowns,version=excluded.version,
                    updated_at=excluded.updated_at
                """,
                (
                    str(item.id),
                    item.statement,
                    item.confidence,
                    str(item.state),
                    _json_dumps(list(item.unknowns)),
                    item.version,
                    _iso(item.updated_at),
                ),
            )
            for evidence_id in item.supporting_evidence:
                self.db.execute(
                    """
                    INSERT INTO belief_evidence(belief_id,evidence_id,relation) VALUES (?,?,'supports')
                    ON CONFLICT(belief_id,evidence_id) DO UPDATE SET relation='supports'
                    """,
                    (str(item.id), str(evidence_id)),
                )
            for evidence_id in item.contradicting_evidence:
                self.db.execute(
                    """
                    INSERT INTO belief_evidence(belief_id,evidence_id,relation) VALUES (?,?,'contradicts')
                    ON CONFLICT(belief_id,evidence_id) DO UPDATE SET relation='contradicts'
                    """,
                    (str(item.id), str(evidence_id)),
                )
            self.db.commit()
        elif isinstance(item, Evidence):
            metadata = dict(item.metadata)
            metadata["source_id"] = item.source_id
            self.db.execute(
                """
                INSERT INTO evidence(id,observation_id,claim,reliability,stance,created_at,metadata)
                VALUES (?,?,?,?,'neutral',?,?)
                ON CONFLICT(id) DO UPDATE SET claim=excluded.claim,
                    reliability=excluded.reliability,metadata=excluded.metadata
                """,
                (
                    str(item.id),
                    str(item.observation_id) if item.observation_id else None,
                    item.claim,
                    item.reliability,
                    _iso(item.created_at),
                    _json_dumps(metadata),
                ),
            )
            self.db.commit()
        elif isinstance(item, Prediction):
            # Prediction persistence normally flows through TursoPredictionStore.
            # Keeping this fallback preserves InMemoryBrainStore.save semantics.
            self.predictions[item.id] = item
            return
        else:
            return InMemoryBrainStore.save(self, item)
        InMemoryBrainStore.save(self, item)

    def upsert_node(self, node: Node) -> None:
        self.db.execute(
            """
            INSERT INTO graph_nodes(id,kind,node_key,properties) VALUES (?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,node_key=excluded.node_key,
                properties=excluded.properties
            """,
            (str(node.id), node.kind, node.key, _json_dumps(dict(node.properties))),
        )
        self.db.commit()
        InMemoryBrainStore.upsert_node(self, node)

    def upsert_edge(self, edge: Edge) -> None:
        self.db.execute(
            """
            INSERT INTO graph_edges(id,source_id,target_id,relation,weight,confidence,evidence_ids,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET source_id=excluded.source_id,
                target_id=excluded.target_id,relation=excluded.relation,
                weight=excluded.weight,confidence=excluded.confidence,
                evidence_ids=excluded.evidence_ids,updated_at=excluded.updated_at
            """,
            (
                str(edge.id),
                str(edge.source),
                str(edge.target),
                edge.relation,
                edge.weight,
                edge.confidence,
                _json_dumps(list(edge.evidence_ids)),
                _iso(edge.updated_at),
            ),
        )
        self.db.commit()
        InMemoryBrainStore.upsert_edge(self, edge)

    def log_rewire(self, event: RewireEvent) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO rewire_events(
                id,operation,target_id,reason,previous,current,evidence_ids,created_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                str(event.id),
                str(event.operation),
                str(event.target_id),
                event.reason,
                _json_dumps(dict(event.previous)),
                _json_dumps(dict(event.current)),
                _json_dumps(list(event.evidence_ids)),
                _iso(event.created_at),
            ),
        )
        self.db.commit()
        InMemoryBrainStore.log_rewire(self, event)
