"""Infrastructure adapters for the Brain runtime."""

from __future__ import annotations

__all__ = [
    "PostgresEventStore",
    "PostgresBrainStore",
    "Neo4jProjection",
    "ObjectStorage",
    "S3ObjectStorage",
    "infrastructure_status",
    "store_evidence_blob",
    "store_cognitive_blob",
    "merge_object_ref_into_metadata",
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
    if name in {
        "store_evidence_blob",
        "store_cognitive_blob",
        "merge_object_ref_into_metadata",
        "object_storage_from_env",
        "object_ref_metadata",
    }:
        from . import evidence_blob_store

        return getattr(evidence_blob_store, name)
    raise AttributeError(name)
