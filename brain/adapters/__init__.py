"""Infrastructure adapters for the Brain runtime."""

from __future__ import annotations

__all__ = [
    "PostgresEventStore",
    "PostgresBrainStore",
    "Neo4jProjection",
    "ObjectStorage",
    "S3ObjectStorage",
    "infrastructure_status",
]


def __getattr__(name: str):
    if name == "PostgresEventStore":
        from .postgres import PostgresEventStore

        return PostgresEventStore
    if name == "PostgresBrainStore":
        from .brain_store import PostgresBrainStore

        return PostgresBrainStore
    if name == "Neo4jProjection":
        from .neo4j_projection import Neo4jProjection

        return Neo4jProjection
    if name == "ObjectStorage":
        from .object_storage import ObjectStorage

        return ObjectStorage
    if name == "S3ObjectStorage":
        from .object_storage import S3ObjectStorage

        return S3ObjectStorage
    if name == "infrastructure_status":
        from .infra_health import infrastructure_status

        return infrastructure_status
    raise AttributeError(name)
