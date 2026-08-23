#!/usr/bin/env python3
"""Validate the Brain archive manifest and any present archive assets.

The archive payload is allowed to remain pending while file-byte upload is not
available, but the manifest must stay valid and any present archive asset must
match its recorded byte count and SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "docs/archive/archive_manifest.json"


REQUIRED_ITEM_KEYS = {
    "filename",
    "target_path",
    "bytes",
    "sha256",
    "media_type",
    "required",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_safe_repo_path(path_value: str, field: str) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        fail(f"{field} must be a non-empty string")
    if path_value.startswith("/"):
        fail(f"{field} must be repo-relative, not absolute: {path_value}")
    if ".." in Path(path_value).parts:
        fail(f"{field} must not contain parent traversal: {path_value}")
    return REPO_ROOT / path_value


def validate_sha256(value: Any, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        fail(f"{field} must be a 64-character SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError:
        fail(f"{field} contains non-hex characters")


def validate_bytes(value: Any, field: str) -> None:
    if not isinstance(value, int) or value <= 0:
        fail(f"{field} must be a positive integer")


def validate_asset_record(record: dict[str, Any], index: int, allow_missing: bool) -> tuple[int, int]:
    missing_keys = REQUIRED_ITEM_KEYS.difference(record)
    if missing_keys:
        fail(f"items[{index}] missing keys: {', '.join(sorted(missing_keys))}")

    target_path = validate_safe_repo_path(record["target_path"], f"items[{index}].target_path")
    validate_bytes(record["bytes"], f"items[{index}].bytes")
    validate_sha256(record["sha256"], f"items[{index}].sha256")

    if not isinstance(record["required"], bool):
        fail(f"items[{index}].required must be boolean")

    if not target_path.exists():
        if record["required"] and not allow_missing:
            fail(f"required archive asset missing: {record['target_path']}")
        warn(f"archive asset pending: {record['target_path']}")
        return (0, 1)

    actual_size = target_path.stat().st_size
    if actual_size != record["bytes"]:
        fail(
            f"size mismatch for {record['target_path']}: "
            f"expected {record['bytes']}, got {actual_size}"
        )

    actual_hash = sha256_file(target_path)
    if actual_hash != record["sha256"]:
        fail(
            f"sha256 mismatch for {record['target_path']}: "
            f"expected {record['sha256']}, got {actual_hash}"
        )

    print(f"OK: archive asset verified: {record['target_path']}")
    return (1, 0)


def main() -> int:
    if not MANIFEST_PATH.is_file():
        fail("docs/archive/archive_manifest.json is missing")

    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"archive_manifest.json is invalid JSON: {exc}")

    required_top_level = ["archive_id", "title", "status", "rule", "source_package", "items"]
    missing_top_level = [key for key in required_top_level if key not in manifest]
    if missing_top_level:
        fail(f"archive_manifest.json missing keys: {', '.join(missing_top_level)}")

    if not isinstance(manifest["items"], list) or not manifest["items"]:
        fail("archive_manifest.json items must be a non-empty list")

    source_package = manifest["source_package"]
    if not isinstance(source_package, dict):
        fail("source_package must be an object")

    for key in ["filename", "target_path", "bytes", "sha256"]:
        if key not in source_package:
            fail(f"source_package missing key: {key}")

    validate_safe_repo_path(source_package["target_path"], "source_package.target_path")
    validate_bytes(source_package["bytes"], "source_package.bytes")
    validate_sha256(source_package["sha256"], "source_package.sha256")

    allow_missing = manifest.get("status") == "assets_pending_file_byte_upload"

    verified = 0
    pending = 0
    for index, record in enumerate(manifest["items"]):
        if not isinstance(record, dict):
            fail(f"items[{index}] must be an object")
        ok, missing = validate_asset_record(record, index, allow_missing=allow_missing)
        verified += ok
        pending += missing

    package_path = REPO_ROOT / source_package["target_path"]
    if package_path.exists():
        actual_size = package_path.stat().st_size
        if actual_size != source_package["bytes"]:
            fail(
                f"source package size mismatch: expected {source_package['bytes']}, got {actual_size}"
            )
        actual_hash = sha256_file(package_path)
        if actual_hash != source_package["sha256"]:
            fail(
                f"source package sha256 mismatch: expected {source_package['sha256']}, got {actual_hash}"
            )
        print(f"OK: source package verified: {source_package['target_path']}")
    else:
        if allow_missing:
            warn(f"source package pending: {source_package['target_path']}")
        else:
            fail(f"source package missing: {source_package['target_path']}")

    print(
        "Archive manifest validation passed. "
        f"Verified assets: {verified}. Pending assets: {pending}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
