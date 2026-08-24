from __future__ import annotations

from typing import Any
from uuid import UUID

try:
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover - infrastructure dependency guard
    dict_row = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc,assignment]

from ..domain import Belief, BeliefState, Edge, Evidence, Node, RewireEvent, RewireOperation
from ..memory import InMemoryBrainStore
from .postgres import PostgresEventStore


def _json(value: Any) -> Any:
    return Jsonb(value) if Jsonb is not None else value


class PostgresBrainStore(InMemoryBrainStore):
    """Write-through canonical Brain state backed by PostgreSQL.

    The in-memory dictionaries are disposable projections used by the existing
    runtime interface. PostgreSQL remains authoritative and the projection is
    rebuilt at startup, so process restarts do not erase beliefs or graph state.
    """

    def __init__(self, dsn: str, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and Jsonb is None:
            raise RuntimeError("PostgreSQL support requires project dependencies")
        super().__init__()
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)
        self.event_store = PostgresEventStore(dsn, pool=self.pool)
        self.hydrate()

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def database_healthy(self, *, timeout: float = 3.0) -> bool:
        # Explicit timeout matters: without it, pool.connection() falls back
        # to the pool's own default (30s), so a genuine DB outage would hang
        # this check -- and therefore /health and /ready -- for 30s instead
        # of failing fast. Confirmed by testing with Postgres actually
        # stopped: unbounded ~30s vs ~3s with this timeout.
        try:
            with self.pool.connection(timeout=timeout) as conn:
                row = conn.execute("select 1").fetchone()
                return bool(row and row[0] == 1)
        except Exception:
            return False

    def hydrate(self) -> None:
        self.beliefs.clear()
        self.evidence.clear()
        self.nodes.clear()
        self.edges.clear()
        self.rewires.clear()
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, statement, confidence, state, unknowns, version, updated_at
                from public.beliefs
                """
            )
            for row in cur.fetchall():
                self.beliefs[row["id"]] = Belief(
                    id=row["id"],
                    statement=row["statement"],
                    confidence=float(row["confidence"]),
                    state=BeliefState(row["state"]),
                    unknowns=list(row["unknowns"] or []),
                    updated_at=row["updated_at"],
                    version=int(row["version"]),
                )

            cur.execute(
                """
                select id, observation_id, claim, reliability, created_at, metadata
                from public.evidence
                """
            )
            for row in cur.fetchall():
                metadata = dict(row["metadata"] or {})
                source_id = str(metadata.pop("source_id", "unknown"))
                self.evidence[row["id"]] = Evidence(
                    id=row["id"],
                    observation_id=row["observation_id"],
                    claim=row["claim"],
                    source_id=source_id,
                    reliability=float(row["reliability"]),
                    created_at=row["created_at"],
                    metadata=metadata,
                )

            cur.execute("select belief_id, evidence_id, relation from public.belief_evidence")
            for row in cur.fetchall():
                belief = self.beliefs.get(row["belief_id"])
                if belief is None:
                    continue
                if row["relation"] == "supports":
                    belief.supporting_evidence.add(row["evidence_id"])
                elif row["relation"] == "contradicts":
                    belief.contradicting_evidence.add(row["evidence_id"])

            cur.execute("select id, kind, node_key, properties from public.graph_nodes")
            for row in cur.fetchall():
                self.nodes[row["id"]] = Node(
                    id=row["id"],
                    kind=row["kind"],
                    key=row["node_key"],
                    properties=dict(row["properties"] or {}),
                )

            cur.execute(
                """
                select id, source_id, target_id, relation, weight, confidence,
                       evidence_ids, updated_at
                from public.graph_edges
                """
            )
            for row in cur.fetchall():
                self.edges[row["id"]] = Edge(
                    id=row["id"],
                    source=row["source_id"],
                    target=row["target_id"],
                    relation=row["relation"],
                    weight=float(row["weight"]),
                    confidence=float(row["confidence"]),
                    evidence_ids=set(row["evidence_ids"] or []),
                    updated_at=row["updated_at"],
                )

            cur.execute(
                """
                select id, operation, target_id, reason, previous, current,
                       evidence_ids, created_at
                from public.rewire_events
                order by created_at asc, id asc
                """
            )
            for row in cur.fetchall():
                self.rewires.append(
                    RewireEvent(
                        id=row["id"],
                        operation=RewireOperation(row["operation"]),
                        target_id=row["target_id"],
                        reason=row["reason"],
                        previous=dict(row["previous"] or {}),
                        current=dict(row["current"] or {}),
                        evidence_ids=list(row["evidence_ids"] or []),
                        created_at=row["created_at"],
                    )
                )

    def append(self, event) -> None:
        self.event_store.append(event)
        super().append(event)

    def read_all(self, *, limit: int | None = None):
        return self.event_store.read_all(limit=limit)

    def read_after(self, occurred_at, event_id: UUID):
        return self.event_store.read_after(occurred_at, event_id)

    def save(self, item) -> None:
        if isinstance(item, Belief):
            with self.pool.connection() as conn:
                conn.execute(
                    """
                    insert into public.beliefs (
                        id, statement, confidence, state, unknowns, version, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                        statement = excluded.statement,
                        confidence = excluded.confidence,
                        state = excluded.state,
                        unknowns = excluded.unknowns,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                    """,
                    (
                        item.id,
                        item.statement,
                        item.confidence,
                        str(item.state),
                        _json(list(item.unknowns)),
                        item.version,
                        item.updated_at,
                    ),
                )
                for evidence_id in item.supporting_evidence:
                    conn.execute(
                        """
                        insert into public.belief_evidence (belief_id, evidence_id, relation)
                        values (%s, %s, 'supports')
                        on conflict (belief_id, evidence_id) do update set relation = excluded.relation
                        """,
                        (item.id, evidence_id),
                    )
                for evidence_id in item.contradicting_evidence:
                    conn.execute(
                        """
                        insert into public.belief_evidence (belief_id, evidence_id, relation)
                        values (%s, %s, 'contradicts')
                        on conflict (belief_id, evidence_id) do update set relation = excluded.relation
                        """,
                        (item.id, evidence_id),
                    )
                conn.commit()
        elif isinstance(item, Evidence):
            metadata = dict(item.metadata)
            metadata["source_id"] = item.source_id
            with self.pool.connection() as conn:
                conn.execute(
                    """
                    insert into public.evidence (
                        id, observation_id, claim, reliability, stance, created_at, metadata
                    ) values (%s, %s, %s, %s, 'neutral', %s, %s)
                    on conflict (id) do update set
                        claim = excluded.claim,
                        reliability = excluded.reliability,
                        metadata = excluded.metadata
                    """,
                    (
                        item.id,
                        item.observation_id,
                        item.claim,
                        item.reliability,
                        item.created_at,
                        _json(metadata),
                    ),
                )
                conn.commit()
        else:
            return super().save(item)
        super().save(item)

    def upsert_node(self, node: Node) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.graph_nodes (id, kind, node_key, properties)
                values (%s, %s, %s, %s)
                on conflict (id) do update set
                    kind = excluded.kind,
                    node_key = excluded.node_key,
                    properties = excluded.properties
                """,
                (node.id, node.kind, node.key, _json(dict(node.properties))),
            )
            conn.commit()
        super().upsert_node(node)

    def upsert_edge(self, edge: Edge) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.graph_edges (
                    id, source_id, target_id, relation, weight, confidence, evidence_ids, updated_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                    source_id = excluded.source_id,
                    target_id = excluded.target_id,
                    relation = excluded.relation,
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
                    edge.updated_at,
                ),
            )
            conn.commit()
        super().upsert_edge(edge)

    def log_rewire(self, event: RewireEvent) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.rewire_events (
                    id, operation, target_id, reason, previous, current, evidence_ids, created_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    event.id,
                    str(event.operation),
                    event.target_id,
                    event.reason,
                    _json(dict(event.previous)),
                    _json(dict(event.current)),
                    list(event.evidence_ids),
                    event.created_at,
                ),
            )
            conn.commit()
        super().log_rewire(event)
