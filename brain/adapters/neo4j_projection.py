"""Neo4j projection writer for the Brain associative topology.

PostgreSQL remains the canonical ledger. Neo4j is a rebuildable materialization
used for graph algorithms and operator exploration. Every mutation here must
originate from a ledger-backed node/edge write or an explicit rebuild command.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from ..domain import Edge, Node

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - optional until deps installed
    GraphDatabase = None  # type: ignore[misc,assignment]


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str = "neo4j"

    @classmethod
    def from_env(cls) -> Neo4jConfig | None:
        uri = os.environ.get("NEO4J_URI", "").strip()
        if not uri:
            return None
        return cls(
            uri=uri,
            user=os.environ.get("NEO4J_USER", "neo4j"),
            password=os.environ.get("NEO4J_PASSWORD", ""),
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        )


class Neo4jProjection:
    """Write-through / rebuild projection of Brain nodes and edges into Neo4j."""

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

    def ensure_constraints(self) -> None:
        statements = (
            "CREATE CONSTRAINT brain_node_id IF NOT EXISTS "
            "FOR (n:BrainNode) REQUIRE n.id IS UNIQUE",
        )
        with self.driver.session(database=self.config.database) as session:
            for stmt in statements:
                try:
                    session.run(stmt)
                except Exception:
                    pass

    def upsert_node(self, node: Node) -> None:
        props = {
            "id": str(node.id),
            "kind": node.kind,
            "key": node.key,
            **{f"p_{k}": _neo4j_value(v) for k, v in (node.properties or {}).items()},
        }
        cypher = """
        MERGE (n:BrainNode {id: $id})
        SET n.kind = $kind,
            n.key = $key,
            n += $props
        """
        with self.driver.session(database=self.config.database) as session:
            session.run(
                cypher,
                id=str(node.id),
                kind=node.kind,
                key=node.key,
                props=props,
            )

    def upsert_edge(self, edge: Edge) -> None:
        cypher = """
        MERGE (s:BrainNode {id: $source})
        MERGE (t:BrainNode {id: $target})
        MERGE (s)-[r:BRAIN_REL {id: $id}]->(t)
        SET r.relation = $relation,
            r.weight = $weight,
            r.confidence = $confidence,
            r.evidence_ids = $evidence_ids,
            r.updated_at = $updated_at
        """
        with self.driver.session(database=self.config.database) as session:
            session.run(
                cypher,
                id=str(edge.id),
                source=str(edge.source),
                target=str(edge.target),
                relation=edge.relation,
                weight=float(edge.weight),
                confidence=float(edge.confidence),
                evidence_ids=[str(x) for x in edge.evidence_ids],
                updated_at=edge.updated_at.isoformat() if edge.updated_at else None,
            )

    def delete_edge(self, edge_id: UUID) -> None:
        with self.driver.session(database=self.config.database) as session:
            session.run(
                "MATCH ()-[r:BRAIN_REL {id: $id}]->() DELETE r",
                id=str(edge_id),
            )

    def rebuild(self, nodes: Iterable[Node], edges: Iterable[Edge]) -> dict[str, int]:
        """Destroy and rebuild the Brain projection from canonical Postgres state."""
        node_list = list(nodes)
        edge_list = list(edges)
        with self.driver.session(database=self.config.database) as session:
            session.run("MATCH (n:BrainNode) DETACH DELETE n")
        self.ensure_constraints()
        for node in node_list:
            self.upsert_node(node)
        for edge in edge_list:
            self.upsert_edge(edge)
        return {"nodes": len(node_list), "edges": len(edge_list)}

    @classmethod
    def from_env(cls) -> Neo4jProjection | None:
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
    if isinstance(value, list):
        return [_neo4j_value(v) for v in value]
    return str(value)
