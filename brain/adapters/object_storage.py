"""S3-compatible object storage for immutable Brain artifacts and evidence payloads.

Works with AWS S3, Cloudflare R2, MinIO, and other S3 API endpoints.
PostgreSQL stores object keys and metadata; bytes live in object storage.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore[assignment]
    ClientError = Exception  # type: ignore[misc,assignment]


@dataclass(frozen=True)
class ObjectStorageConfig:
    bucket: str
    region: str = "us-east-1"
    endpoint_url: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    prefix: str = "brain/"

    @classmethod
    def from_env(cls) -> ObjectStorageConfig | None:
        bucket = os.environ.get("OBJECT_STORAGE_BUCKET", "").strip()
        if not bucket:
            return None
        endpoint = os.environ.get("OBJECT_STORAGE_ENDPOINT", "").strip() or None
        return cls(
            bucket=bucket,
            region=os.environ.get("OBJECT_STORAGE_REGION", "us-east-1"),
            endpoint_url=endpoint,
            access_key_id=os.environ.get("OBJECT_STORAGE_ACCESS_KEY")
            or os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.environ.get("OBJECT_STORAGE_SECRET_KEY")
            or os.environ.get("AWS_SECRET_ACCESS_KEY"),
            prefix=os.environ.get("OBJECT_STORAGE_PREFIX", "brain/"),
        )


class ObjectStorage:
    """Put/get/delete immutable artifacts under a stable key namespace."""

    def __init__(self, config: ObjectStorageConfig, *, client: Any | None = None) -> None:
        if boto3 is None and client is None:
            raise RuntimeError("boto3 is required for ObjectStorage; pip install boto3")
        self.config = config
        if client is not None:
            self.client = client
        else:
            kwargs: dict[str, Any] = {"region_name": config.region}
            if config.endpoint_url:
                kwargs["endpoint_url"] = config.endpoint_url
            if config.access_key_id and config.secret_access_key:
                kwargs["aws_access_key_id"] = config.access_key_id
                kwargs["aws_secret_access_key"] = config.secret_access_key
            self.client = boto3.client("s3", **kwargs)

    def healthy(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.config.bucket)
            return True
        except Exception:
            try:
                self.client.list_objects_v2(Bucket=self.config.bucket, MaxKeys=1)
                return True
            except Exception:
                return False

    def _key(self, object_key: str) -> str:
        key = object_key.lstrip("/")
        prefix = self.config.prefix
        if prefix and not key.startswith(prefix):
            return f"{prefix}{key}"
        return key

    def put_bytes(
        self,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        object_key: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        key = self._key(object_key or f"artifacts/{digest[:2]}/{digest}")
        self.client.put_object(
            Bucket=self.config.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": digest, **(metadata or {})},
        )
        return {
            "bucket": self.config.bucket,
            "key": key,
            "sha256": digest,
            "size": str(len(data)),
            "content_type": content_type,
            "uri": f"s3://{self.config.bucket}/{key}",
        }

    def put_file(
        self,
        path: str,
        *,
        content_type: str = "application/octet-stream",
        object_key: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        with open(path, "rb") as fh:
            return self.put_bytes(
                fh.read(),
                content_type=content_type,
                object_key=object_key,
                metadata=metadata,
            )

    def get_bytes(self, object_key: str) -> bytes:
        response = self.client.get_object(
            Bucket=self.config.bucket, Key=self._key(object_key)
        )
        return response["Body"].read()

    def delete(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.config.bucket, Key=self._key(object_key))

    def exists(self, object_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.config.bucket, Key=self._key(object_key))
            return True
        except ClientError:
            return False
        except Exception:
            return False

    def new_evidence_key(self, *, suffix: str = "bin") -> str:
        return f"evidence/{uuid4().hex}.{suffix}"

    @classmethod
    def from_env(cls) -> ObjectStorage | None:
        config = ObjectStorageConfig.from_env()
        if config is None:
            return None
        return cls(config)
