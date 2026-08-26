#!/usr/bin/env python3
"""Rebuild one tenant's Neo4j projection from canonical PostgreSQL graph rows."""

from __future__ import annotations

import os
import sys
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from brain.adapters.neo4j_projection import Neo4jProjection
from brain.domain import Edge, Node
from brain.tenant_runtime import require_safe_runtime_role, tenant_rls_enforced


def _required_uuid(name: str) -> UUID:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    try:
        return UUID(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid UUID") from exc


def _load_graph(dsn: str, tenant_id: UUID) -> tuple[list[Node], list[Edge]]:
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
            nodes, edges = _load_graph(dsn, tenant_id)
            result = projection.rebuild(nodes, edges, scope=tenant_id)
        finally:
            projection.close()
    except Exception as exc:
        print(f"neo4j projection rebuild failed: {exc}", file=sys.stderr)
        return 2

    print(f"rebuilt tenant {tenant_id} neo4j projection: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
