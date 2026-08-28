from __future__ import annotations

import threading
import time
from math import isfinite
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

from ..beliefs import rebuild_fingerprints
from ..logging_config import get_logger
from ..domain import Belief, BeliefState, Edge, Evidence, Node, RewireEvent, RewireOperation
from ..memory import InMemoryBrainStore
from .postgres import PostgresEventStore


log = get_logger("brain_store")


def _json(value: Any) -> Any:
    return Jsonb(value) if Jsonb is not None else value


class PostgresBrainStore(InMemoryBrainStore):
    """Write-through canonical Brain state backed by PostgreSQL.

    The in-memory dictionaries are disposable projections used by the existing
    runtime interface. PostgreSQL remains authoritative and the projection is
    rebuilt at startup, so process restarts do not erase beliefs or graph state.
    """

    #: Ceiling on how long a read path will wait for a pooled connection.
    #: psycopg_pool's own default is 30s, so a database that has gone away
    #: turns every projection read into a half-minute hang -- and the cockpit
    #: polls eighteen of them at once. Failing in a few seconds and serving
    #: the last good projection is the better answer; #75 bounded the health
    #: check for the same reason.
    READ_TIMEOUT_SECONDS = 5.0

    def __init__(self, dsn: str, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and Jsonb is None:
            raise RuntimeError("PostgreSQL support requires project dependencies")
        super().__init__()
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)
        self.event_store = PostgresEventStore(dsn, pool=self.pool)
        self._refresh_lock = threading.Lock()
        self._counters_lock = threading.Lock()
        self._counters: tuple[float, dict[str, int] | None] = (0.0, None)
        # Deliberately not _refresh_lock: that one is held across the whole
        # hydrate, and a write must never block waiting for a read to finish.
        self._inflight_lock = threading.Lock()
        self._inflight: dict[str, dict] | None = None
        self.hydrate()
        # The constructor's hydrate is the first refresh; without stamping it
        # here the first refresh_if_stale would immediately hydrate again.
        self._hydrated_at: float | None = time.monotonic()

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
        """Rebuild the projection from PostgreSQL, atomically.

        Every collection is built to one side and only swapped in once the
        whole read succeeded. Two things depended on that:

        Clearing first meant a database that went away mid-refresh left the
        API serving an *empty* projection -- no beliefs, no graph -- which
        reads as a Brain that has forgotten everything rather than one that
        could not reach its database. The last good projection is strictly
        better than a blank one.

        And the swap rebinds the attributes instead of mutating the live
        dictionaries, so a reader that is already iterating one of them keeps
        a complete snapshot rather than watching it empty out underneath --
        the Observatory polls several projection-backed routes at once, so a
        refresh always lands mid-iteration somewhere.
        """

        with self._inflight_lock:
            self._inflight = {
                "beliefs": {},
                "evidence": {},
                "nodes": {},
                "edges": {},
                "rewires": [],
            }
        try:
            beliefs, evidence, nodes, edges, rewires = self._load_projection()
        except BaseException:
            with self._inflight_lock:
                self._inflight = None
            raise

        # Draining and swapping are one step, under the same lock every local
        # write takes. Draining first and assigning afterwards left an
        # interval where a write mutated the *old* projection, saw no in-flight
        # buffer to record itself in, and was then thrown away by the
        # assignment -- the very loss the buffer was added to prevent, moved a
        # few lines later. Inside the lock there is nowhere for a write to
        # land: it either recorded itself before the drain, or it mutates the
        # new projection after the swap.
        with self._inflight_lock:
            pending, self._inflight = self._inflight, None
            # Writes that landed during the load win over what was read: a
            # load is a series of queries, not an instant, so a belief can be
            # committed after the belief query has already run.
            beliefs.update(pending["beliefs"])
            evidence.update(pending["evidence"])
            nodes.update(pending["nodes"])
            edges.update(pending["edges"])
            rewires.extend(pending["rewires"])

            self.beliefs = beliefs
            self.evidence = evidence
            self.nodes = nodes
            self.edges = edges
            self.rewires = rewires

    def _apply_local(self, item: Any, method: Any) -> None:
        """Mutate the live projection and record the write as one step.

        Both halves under one lock, because a write that has updated the
        in-memory projection but not yet recorded itself is exactly the write
        a concurrent swap loses.
        """

        with self._inflight_lock:
            method(self, item)
            pending = self._inflight
            if pending is None:
                return
            if isinstance(item, Belief):
                pending["beliefs"][item.id] = item
            elif isinstance(item, Evidence):
                pending["evidence"][item.id] = item
            elif isinstance(item, Node):
                pending["nodes"][item.id] = item
            elif isinstance(item, Edge):
                pending["edges"][item.id] = item
            elif isinstance(item, RewireEvent):
                pending["rewires"].append(item)

    def _load_projection(
        self,
    ) -> tuple[
        dict[UUID, Belief],
        dict[UUID, Evidence],
        dict[UUID, Node],
        dict[UUID, Edge],
        list[RewireEvent],
    ]:
        beliefs: dict[UUID, Belief] = {}
        evidence: dict[UUID, Evidence] = {}
        nodes: dict[UUID, Node] = {}
        edges: dict[UUID, Edge] = {}
        rewires: list[RewireEvent] = []
        with self.pool.connection(timeout=self.READ_TIMEOUT_SECONDS) as conn, conn.cursor(
            row_factory=dict_row
        ) as cur:
            self._bound_statements(cur)
            cur.execute(
                """
                select id, statement, confidence, state, unknowns, version, updated_at
                from public.beliefs
                """
            )
            for row in cur.fetchall():
                beliefs[row["id"]] = Belief(
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
                evidence[row["id"]] = Evidence(
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
                belief = beliefs.get(row["belief_id"])
                if belief is None:
                    continue
                if row["relation"] == "supports":
                    belief.supporting_evidence.add(row["evidence_id"])
                elif row["relation"] == "contradicts":
                    belief.contradicting_evidence.add(row["evidence_id"])

            # Rebuild the derived dedup set now that beliefs and evidence are
            # both loaded, so a restart cannot let an already-counted claim
            # move confidence a second time.
            for belief in beliefs.values():
                rebuild_fingerprints(belief, evidence)

            cur.execute("select id, kind, node_key, properties from public.graph_nodes")
            for row in cur.fetchall():
                nodes[row["id"]] = Node(
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
                edges[row["id"]] = Edge(
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
                rewires.append(
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

        return beliefs, evidence, nodes, edges, rewires

    #: Durable markers of cognition. Counted through brain_events_type_idx
    #: (event_type, occurred_at) from migration 001, so this stays an indexed
    #: grouped count rather than the full brain_events scan #75 removed.
    COGNITION_EVENT_TYPES = (
        "cycle.completed",
        "signal.enqueued",
        "observation.received",
        "belief.created",
        "belief.updated",
    )

    def cognition_counters(self, max_age_seconds: float = 0.0) -> dict[str, int]:
        """Counts of cognition events actually recorded in the database.

        Reporting the answering process's own counters was always zero in the
        API, because cognition happens elsewhere -- in the worker, or in this
        process's inline loop, but either way against a HeartbeatService the
        request path never touches. These counts come from the shared event
        stream, so they describe the system rather than whoever answered.

        Cached for ``max_age_seconds``. The index makes this a grouped count
        over matching entries rather than a full scan, but "not a scan" is not
        "constant time": the work still grows with the lifetime event history,
        and the Observatory asks for it twice per poll, every five seconds,
        forever. Caching bounds that to one count per interval no matter how
        many readers or routes ask.
        """

        # The whole thing under the lock, miss included. Releasing it before
        # the query let concurrent /health and /runner/status polls each see
        # the same stale entry and run the count independently -- defeating
        # the one-query-per-interval bound on precisely the parallel polling
        # it exists to bound.
        with self._counters_lock:
            if isfinite(max_age_seconds) and max_age_seconds > 0:
                counted_at, cached = self._counters
                if cached is not None and time.monotonic() - counted_at < max_age_seconds:
                    return dict(cached)
            counts = self._count_cognition_events()
            self._counters = (time.monotonic(), counts)
            return dict(counts)

    def _bound_statements(self, cur: Any) -> None:
        """Cap how long the server will spend on this connection's reads.

        pool.connection(timeout=...) bounds only *checking out* a connection.
        Once psycopg has one, the query itself runs with no client-side
        deadline at all, so a lock or a slow plan can hold a read far past
        READ_TIMEOUT_SECONDS. PostgreSQL's own statement_timeout is the only
        thing that actually bounds execution.

        set_config(), not SET. SET is parsed before parameters are bound, so
        `set statement_timeout = %s` is a syntax error on the server -- and
        because it fails *inside* the transaction, it aborts it, and every
        query after it dies with "current transaction is aborted" rather than
        anything that names the real cause. set_config is an ordinary function
        call and takes its value as a parameter. Its third argument makes the
        setting transaction-local, so it cannot leak onto a pooled connection
        that some later caller checks out for something slower on purpose.
        """

        try:
            cur.execute(
                "select set_config('statement_timeout', %s, true)",
                (str(int(self.READ_TIMEOUT_SECONDS * 1000)),),
            )
        except Exception:
            # A store pointed at something that does not understand the
            # setting should still be readable; the checkout bound remains.
            log.warning("statement_timeout could not be set", exc_info=True)

    def _count_cognition_events(self) -> dict[str, int]:
        with self.pool.connection(timeout=self.READ_TIMEOUT_SECONDS) as conn, conn.cursor() as cur:
            self._bound_statements(cur)
            cur.execute(
                """
                select event_type, count(*)
                from public.brain_events
                where event_type = any(%s)
                group by event_type
                """,
                (list(self.COGNITION_EVENT_TYPES),),
            )
            return {str(row[0]): int(row[1]) for row in cur.fetchall()}

    def refresh_if_stale(self, max_age_seconds: float) -> bool:
        """Re-read the belief/graph projection when the cached copy has aged out.

        hydrate() runs once at startup, so a long-lived API process served the
        snapshot it booted with and never saw anything the worker wrote
        afterwards. Refreshing on a TTL keeps reads live without paying a full
        hydrate per request: the Observatory polls every 5s, so at the default
        TTL this costs about one hydrate per poll interval regardless of how
        many readers there are.

        Returns True when a refresh actually ran.
        """
        if not isfinite(max_age_seconds) or max_age_seconds < 0:
            return False
        with self._refresh_lock:
            now = time.monotonic()
            if self._hydrated_at is not None and now - self._hydrated_at < max_age_seconds:
                return False
            # The whole refresh happens under the lock, not just the decision
            # to run one. Releasing it first let a second reader see a fresh
            # timestamp and skip its own refresh while the first was still
            # loading -- and the TTL is only honest if it starts when the
            # projection is actually new. Concurrent readers wait for one
            # hydrate instead of stampeding the database with several.
            self.hydrate()
            # Stamped only on success: a failed refresh that advanced the
            # clock would suppress every retry for the length of the TTL.
            self._hydrated_at = time.monotonic()
        return True

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
            self._apply_local(item, InMemoryBrainStore.save)
            return
        self._apply_local(item, InMemoryBrainStore.save)

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
        self._apply_local(node, InMemoryBrainStore.upsert_node)

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
        self._apply_local(edge, InMemoryBrainStore.upsert_edge)

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
        self._apply_local(event, InMemoryBrainStore.log_rewire)
