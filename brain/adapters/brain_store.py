from __future__ import annotations

from typing import Any
from uuid import UUID

try:
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover
    dict_row = None  # type: ignore[misc,assignment]
    Jsonb = None  # type: ignore[misc,assignment]
    ConnectionPool = None  # type: ignore[misc,assignment]

from ..domain import Belief, Edge, Evidence, Node, Prediction, RewireEvent
from ..runtime import InMemoryBrainStore
from .postgres import PostgresEventStore


class PostgresBrainStore(InMemoryBrainStore):
    """PostgreSQL-backed BrainStore with optional Neo4j graph projection.

    The in-memory dictionaries are disposable projections used by the existing
    runtime interface. PostgreSQL remains authoritative and the projection is
    rebuilt at startup, so process restarts do not erase beliefs or graph state.

    When NEO4J_URI is set, graph node/edge writes are also projected to Neo4j.
    Neo4j remains rebuildable; Postgres stays canonical.
    """

    def __init__(self, dsn: str, *, pool: ConnectionPool | None = None) -> None:
        super().__init__()
        self.dsn = dsn
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)
        self.event_store = PostgresEventStore(dsn, pool=self.pool)
        self._neo4j = None
        try:
            from .neo4j_projection import Neo4jProjection

            self._neo4j = Neo4jProjection.from_env()
            if self._neo4j is not None:
                self._neo4j.ensure_constraints()
        except Exception:
            # Graph projection is optional; Postgres remains canonical.
            self._neo4j = None
        self.hydrate()

    def close(self) -> None:
        if getattr(self, "_neo4j", None) is not None:
            try:
                self._neo4j.close()
            except Exception:
                pass
            self._neo4j = None
        if self._owns_pool:
            self.pool.close()

    def database_healthy(self, *, timeout: float = 3.0) -> bool:
        try:
            with self.pool.connection(timeout=timeout) as conn:
                row = conn.execute("select 1").fetchone()
                return bool(row and row[0] == 1)
        except Exception:
            return False

    def rebuild_neo4j_projection(self) -> dict[str, int]:
        """Rebuild Neo4j from canonical Postgres graph tables (or in-memory projection)."""
        if self._neo4j is None:
            raise RuntimeError("Neo4j projection is not configured (set NEO4J_URI)")
        return self._neo4j.rebuild(self.nodes.values(), self.edges.values())
