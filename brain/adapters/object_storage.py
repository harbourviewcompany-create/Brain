"""Immutable S3-compatible object storage adapter."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ObjectRef:
    key: str
    sha256: str
    bytes: int
    url: str


class ObjectStorage(Protocol):
    def put_bytes(self, data: bytes, *, key: str | None = None) -> ObjectRef: ...
    def put_file(self, path: str | Path, *, key: str | None = None) -> ObjectRef: ...
    def get_bytes(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class S3ObjectStorage:
    """Write-once object storage with content-addressed defaults."""

    def __init__(self, bucket: str, *, client: Any, prefix: str = "") -> None:
        self.bucket = bucket
        self.client = client
        normalized = prefix.strip("/")
        self.prefix = f"{normalized}/" if normalized else ""

    @classmethod
    def from_env(cls) -> "S3ObjectStorage | None":
        bucket = os.environ.get("OBJECT_STORAGE_BUCKET", "").strip()
        if not bucket:
            return None
        if boto3 is None:
            raise RuntimeError("boto3 is required for S3ObjectStorage")

        kwargs: dict[str, Any] = {
            "region_name": os.environ.get("OBJECT_STORAGE_REGION", "us-east-1"),
        }
        endpoint = os.environ.get("OBJECT_STORAGE_ENDPOINT", "").strip()
        if endpoint:
            kwargs["endpoint_url"] = endpoint

        access_key = os.environ.get("OBJECT_STORAGE_ACCESS_KEY", "").strip()
        secret_key = os.environ.get("OBJECT_STORAGE_SECRET_KEY", "")
        session_token = os.environ.get("OBJECT_STORAGE_SESSION_TOKEN", "")
        if access_key or secret_key or session_token:
            if not access_key or not secret_key:
                raise RuntimeError(
                    "OBJECT_STORAGE_ACCESS_KEY and OBJECT_STORAGE_SECRET_KEY "
                    "must be set together"
                )
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
            if session_token:
                kwargs["aws_session_token"] = session_token

        return cls(
            bucket,
            client=boto3.client("s3", **kwargs),
            prefix=os.environ.get("OBJECT_STORAGE_PREFIX", ""),
        )

    def _full_key(self, key: str) -> str:
        value = key.lstrip("/")
        if not value:
            raise ValueError("object key must not be empty")
        return f"{self.prefix}{value}"

    def _existing_digest(self, key: str) -> str | None:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            if _not_found(exc):
                return None
            raise
        return (response.get("Metadata") or {}).get("sha256")

    def _put_stream(
        self,
        body: BinaryIO | bytes,
        *,
        key: str,
        digest: str,
        byte_count: int,
    ) -> ObjectRef:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                Metadata={"sha256": digest},
                IfNoneMatch="*",
            )
        except Exception as exc:
            if not _precondition_failed(exc):
                raise
            existing = self._existing_digest(key)
            if existing != digest:
                raise RuntimeError(
                    f"immutable object key already exists with different digest: {key}"
                ) from exc
        return ObjectRef(
            key=key,
            sha256=digest,
            bytes=byte_count,
            url=f"s3://{self.bucket}/{key}",
        )

    def put_bytes(self, data: bytes, *, key: str | None = None) -> ObjectRef:
        digest = hashlib.sha256(data).hexdigest()
        object_key = self._full_key(key or f"evidence/{digest}")
        return self._put_stream(data, key=object_key, digest=digest, byte_count=len(data))

    def put_file(self, path: str | Path, *, key: str | None = None) -> ObjectRef:
        source = Path(path)
        digest = hashlib.sha256()
        byte_count = 0
        with source.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                byte_count += len(chunk)
        digest_hex = digest.hexdigest()
        object_key = self._full_key(key or f"evidence/{digest_hex}")
        with source.open("rb") as handle:
            return self._put_stream(
                handle,
                key=object_key,
                digest=digest_hex,
                byte_count=byte_count,
            )

    def get_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=self._full_key(key))
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._full_key(key))


def _error_code(exc: Exception) -> str:
    response = getattr(exc, "response", {}) or {}
    error = response.get("Error", {}) or {}
    return str(error.get("Code", ""))


def _precondition_failed(exc: Exception) -> bool:
    return _error_code(exc) in {"PreconditionFailed", "412"}


def _not_found(exc: Exception) -> bool:
    return _error_code(exc) in {"NoSuchKey", "NotFound", "404"}
