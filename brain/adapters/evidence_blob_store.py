"""Optional routing of evidence / cognitive object bytes into object storage.

PostgreSQL remains the authority for structured evidence and cognitive object
rows. When object storage is configured, callers may place immutable payload
bytes in S3/MinIO and keep only the ObjectRef (key, sha256, size, url) in
Postgres metadata or cognitive payload fields.

This module is opt-in: no automatic dual-write from brain_store.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .object_storage import ObjectRef, S3ObjectStorage


def object_storage_from_env() -> S3ObjectStorage | None:
    """Return configured S3ObjectStorage, or None when bucket is unset."""
    return S3ObjectStorage.from_env()


def store_evidence_blob(
    storage: S3ObjectStorage,
    data: bytes,
    *,
    evidence_id: UUID | str | None = None,
    key: str | None = None,
) -> ObjectRef:
    """Write evidence bytes immutably; key defaults to evidence/<id|digest>."""
    if key is None and evidence_id is not None:
        key = f"evidence/{evidence_id}"
    return storage.put_bytes(data, key=key)


def store_cognitive_blob(
    storage: S3ObjectStorage,
    data: bytes,
    *,
    kind: str,
    object_id: UUID | str,
    key: str | None = None,
) -> ObjectRef:
    """Write cognitive-object bytes; key defaults to cognitive/<kind>/<id>."""
    if key is None:
        key = f"cognitive/{kind}/{object_id}"
    return storage.put_bytes(data, key=key)


def object_ref_metadata(ref: ObjectRef) -> dict[str, Any]:
    """Flatten ObjectRef for JSON metadata / cognitive payload fields."""
    return {
        "object_storage_key": ref.key,
        "object_storage_sha256": ref.sha256,
        "object_storage_bytes": ref.bytes,
        "object_storage_url": ref.url,
    }


def merge_object_ref_into_metadata(
    metadata: dict[str, Any] | None,
    ref: ObjectRef,
) -> dict[str, Any]:
    """Return a copy of metadata with object-storage fields set."""
    out = dict(metadata or {})
    out.update(object_ref_metadata(ref))
    return out
