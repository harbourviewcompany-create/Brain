#!/usr/bin/env python3
"""Rebuild one tenant's Neo4j projection from canonical PostgreSQL graph + evidence."""

from __future__ import annotations

import os
import sys
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from brain.adapters.neo4j_projection import Neo4jProjection
from brain.domain import Edge, Evidence, Node
from brain.tenant_runtime import require_safe_runtime_role, tenant_rls_enforced


def _required_uuid(name: str) -> UUID:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    try:
        return UUID(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid UUID") from exc


def _load_graph(
    dsn: str, tenant_id: UUID
) -> tuple[list[Node], list[Edge], list[Evidence]]:
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        if tenant_rls_enforced(conn):
            require_safe_runtime_role(conn, require_trusted_service=True)

        nodes = conn.execute(
            """
            select id, kind, node_key, properties
            from public.graph_nodes
            where tenant_id = %s
            order by id
            """,
            (tenant_id,),
        ).fetchall()
        edges = conn.execute(
            """
            select id, source_id, target_id, relation, weight, confidence,
                   evidence_ids, updated_at
            from public.graph_edges
            where tenant_id = %s
            order by id
            """,
            (tenant_id,),
        ).fetchall()

        # All tenant evidence rows (edge.evidence_ids still drive JUSTIFIES links).
        evidence_rows = conn.execute(
            """
            select id, observation_id, claim, reliability, created_at, metadata
            from public.evidence
            where tenant_id = %s
            order by id
            """,
            (tenant_id,),
        ).fetchall()

    evidence = []
    for row in evidence_rows:
        metadata = dict(row["metadata"] or {})
        source_id = str(metadata.pop("source_id", "unknown"))
        evidence.append(
            Evidence(
                id=row["id"],
                observation_id=row["observation_id"],
                claim=row["claim"],
                source_id=source_id,
                reliability=float(row["reliability"]),
                created_at=row["created_at"],
                metadata=metadata,
            )
        )

    return (
        [
            Node(
                id=row["id"],
                kind=row["kind"],
                key=row["node_key"],
                properties=dict(row["properties"] or {}),
            )
            for row in nodes
        ],
        [
            Edge(
                id=row["id"],
                source=row["source_id"],
                target=row["target_id"],
                relation=row["relation"],
                weight=float(row["weight"]),
                confidence=float(row["confidence"]),
                evidence_ids=set(row["evidence_ids"] or []),
                updated_at=row["updated_at"],
            )
            for row in edges
        ],
        evidence,
    )


def main() -> int:
    try:
        tenant_id = _required_uuid("BRAIN_NEO4J_REBUILD_TENANT_ID")
        dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL", "").strip()
        if not dsn:
            raise RuntimeError(
                "BRAIN_WORKER_DATABASE_URL is required for tenant-scoped projection rebuilds"
            )

        projection = Neo4jProjection.from_env()
        if projection is None:
            raise RuntimeError("NEO4J_URI and NEO4J_PROJECTION_ENABLED=true are required")

        try:
            nodes, edges, evidence = _load_graph(dsn, tenant_id)
            result = projection.rebuild(nodes, edges, scope=tenant_id, evidence=evidence)
        finally:
            projection.close()
    except Exception as exc:
        print(f"neo4j projection rebuild failed: {exc}", file=sys.stderr)
        return 2

    print(f"rebuilt tenant {tenant_id} neo4j projection: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
