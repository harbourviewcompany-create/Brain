"""Tenant-scoped rebuildable Neo4j projection for Brain graph topology.

PostgreSQL is authoritative. Neo4j is a derived materialization. Projection
operations always include an explicit tenant scope so a rebuild cannot delete
or collide with another tenant's graph.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from ..domain import Edge, Node

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover
    GraphDatabase = None  # type: ignore[misc,assignment]


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str = "neo4j"

    @classmethod
    def from_env(cls) -> "Neo4jConfig | None":
        uri = os.environ.get("NEO4J_URI", "").strip()
        if not uri:
            return None
        user = os.environ.get("NEO4J_USER", "neo4j").strip()
        password = os.environ.get("NEO4J_PASSWORD", "")
        if not user or not password:
            raise RuntimeError("NEO4J_USER and NEO4J_PASSWORD are required when NEO4J_URI is set")
        return cls(
            uri=uri,
            user=user,
            password=password,
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        )


class Neo4jProjection:
    """Tenant-scoped derived projection of canonical PostgreSQL graph rows."""

    def __init__(self, config: Neo4jConfig, *, driver: Any | None = None) -> None:
        if GraphDatabase is None and driver is None:
            raise RuntimeError("neo4j package is required for Neo4jProjection")
        self.config = config
        self._owns_driver = driver is None
        self.driver = driver or GraphDatabase.driver(
            config.uri, auth=(config.user, config.password)
        )

    def close(self) -> None:
        if self._owns_driver:
            self.driver.close()

    def healthy(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    @staticmethod
    def _scope(scope: UUID | str) -> str:
        value = str(scope).strip()
        if not value:
            raise ValueError("tenant scope is required")
        return value

    @staticmethod
    def _projection_id(scope: str, object_id: UUID) -> str:
        return f"{scope}:{object_id}"

    def ensure_constraints(self) -> None:
        statement = (
            "CREATE CONSTRAINT brain_node_projection_id IF NOT EXISTS "
            "FOR (n:BrainNode) REQUIRE n.projection_id IS UNIQUE"
        )
        with self.driver.session(database=self.config.database) as session:
            session.run(statement).consume()

    def upsert_node(self, node: Node, *, scope: UUID | str) -> None:
        tenant_scope = self._scope(scope)
        projection_id = self._projection_id(tenant_scope, node.id)
        props = {
            "projection_id": projection_id,
            "tenant_scope": tenant_scope,
            "id": str(node.id),
            "kind": node.kind,
            "key": node.key,
            **{f"p_{k}": _neo4j_value(v) for k, v in (node.properties or {}).items()},
        }
        with self.driver.session(database=self.config.database) as session:
            session.run(
                """
                MERGE (n:BrainNode {projection_id: $projection_id})
                SET n = $props
                """,
                projection_id=projection_id,
                props=props,
            ).consume()

    def upsert_edge(self, edge: Edge, *, scope: UUID | str) -> None:
        tenant_scope = self._scope(scope)
        projection_id = self._projection_id(tenant_scope, edge.id)
        source_projection_id = self._projection_id(tenant_scope, edge.source)
        target_projection_id = self._projection_id(tenant_scope, edge.target)
        props = {
            "projection_id": projection_id,
            "tenant_scope": tenant_scope,
            "id": str(edge.id),
            "relation": edge.relation,
            "weight": float(edge.weight),
            "confidence": float(edge.confidence),
            "evidence_ids": [str(x) for x in edge.evidence_ids],
            "updated_at": edge.updated_at.isoformat() if edge.updated_at else None,
        }
        with self.driver.session(database=self.config.database) as session:
            session.run(
                """
                MATCH ()-[old:BRAIN_REL {projection_id: $projection_id}]->()
                DELETE old
                """,
                projection_id=projection_id,
            ).consume()
            session.run(
                """
                MERGE (s:BrainNode {projection_id: $source_projection_id})
                ON CREATE SET s.tenant_scope = $tenant_scope, s.id = $source_id
                MERGE (t:BrainNode {projection_id: $target_projection_id})
                ON CREATE SET t.tenant_scope = $tenant_scope, t.id = $target_id
                CREATE (s)-[r:BRAIN_REL]->(t)
                SET r = $props
                """,
                source_projection_id=source_projection_id,
                target_projection_id=target_projection_id,
                tenant_scope=tenant_scope,
                source_id=str(edge.source),
                target_id=str(edge.target),
                props=props,
            ).consume()

    def delete_edge(self, edge_id: UUID, *, scope: UUID | str) -> None:
        tenant_scope = self._scope(scope)
        projection_id = self._projection_id(tenant_scope, edge_id)
        with self.driver.session(database=self.config.database) as session:
            session.run(
                "MATCH ()-[r:BRAIN_REL {projection_id: $projection_id}]->() DELETE r",
                projection_id=projection_id,
            ).consume()

    def rebuild(
        self,
        nodes: Iterable[Node],
        edges: Iterable[Edge],
        *,
        scope: UUID | str,
    ) -> dict[str, int]:
        """Replace exactly one tenant projection from canonical PostgreSQL state."""
        tenant_scope = self._scope(scope)
        node_list = list(nodes)
        edge_list = list(edges)
        with self.driver.session(database=self.config.database) as session:
            session.run(
                "MATCH (n:BrainNode {tenant_scope: $tenant_scope}) DETACH DELETE n",
                tenant_scope=tenant_scope,
            ).consume()
            session.run(
                "MATCH ()-[r:BRAIN_REL {tenant_scope: $tenant_scope}]->() DELETE r",
                tenant_scope=tenant_scope,
            ).consume()
        self.ensure_constraints()
        for node in node_list:
            self.upsert_node(node, scope=tenant_scope)
        for edge in edge_list:
            self.upsert_edge(edge, scope=tenant_scope)
        return {"nodes": len(node_list), "edges": len(edge_list)}

    @classmethod
    def from_env(cls) -> "Neo4jProjection | None":
        config = Neo4jConfig.from_env()
        if config is None:
            return None
        enabled = os.environ.get("NEO4J_PROJECTION_ENABLED", "true").lower()
        if enabled in {"0", "false", "no", "off"}:
            return None
        return cls(config)


def _neo4j_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return [_neo4j_value(v) for v in value]
    if isinstance(value, dict):
        return str(value)
    return str(value)
