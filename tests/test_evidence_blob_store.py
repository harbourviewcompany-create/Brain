"""Unit tests for optional evidence/cognitive blob routing."""

from __future__ import annotations

from uuid import UUID

from brain.adapters.evidence_blob_store import (
    merge_object_ref_into_metadata,
    object_ref_metadata,
    store_cognitive_blob,
    store_evidence_blob,
)
from brain.adapters.object_storage import S3ObjectStorage


class _S3:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Bucket, Key, Body, Metadata, IfNoneMatch):
        assert IfNoneMatch == "*"
        data = Body if isinstance(Body, bytes) else Body.read()
        self.objects[Key] = {"data": data, "Metadata": dict(Metadata)}
        return {}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            exc = Exception("not found")
            exc.response = {"Error": {"Code": "404"}}
            raise exc
        return {"Metadata": self.objects[Key]["Metadata"]}


def test_store_evidence_blob_uses_evidence_id_key():
    storage = S3ObjectStorage("brain", client=_S3())
    eid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    ref = store_evidence_blob(storage, b"claim-bytes", evidence_id=eid)
    assert ref.key == f"evidence/{eid}"
    assert ref.bytes == len(b"claim-bytes")
    assert ref.sha256
    assert ref.url.startswith("s3://brain/")


def test_store_cognitive_blob_uses_kind_and_id():
    storage = S3ObjectStorage("brain", client=_S3())
    oid = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    ref = store_cognitive_blob(storage, b"payload", kind="episode", object_id=oid)
    assert ref.key == f"cognitive/episode/{oid}"


def test_merge_object_ref_into_metadata():
    storage = S3ObjectStorage("brain", client=_S3())
    ref = store_evidence_blob(storage, b"x", key="evidence/custom")
    meta = merge_object_ref_into_metadata({"source_id": "src-1"}, ref)
    assert meta["source_id"] == "src-1"
    assert meta["object_storage_key"] == ref.key
    assert meta["object_storage_sha256"] == ref.sha256
    assert object_ref_metadata(ref)["object_storage_url"] == ref.url
