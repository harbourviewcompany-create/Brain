#!/usr/bin/env python3
"""Ingest the Brain current-thread archive ZIP into repository paths.

This script verifies the ZIP package and every extracted asset against
`docs/archive/archive_manifest.json`, then writes the files into the target
repository paths.

Usage:
    python scripts/ingest_current_thread_archive.py /path/to/Brain_Compilation_Full_Current_Thread_Package.zip --repo-root .

Rules:
    - Do not summarize or alter archive contents.
    - Do not create placeholder files.
    - Fail on missing, renamed, size-mismatched, or hash-mismatched assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST_PATH = Path("docs/archive/archive_manifest.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / DEFAULT_MANIFEST_PATH
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_package(zip_path: Path, manifest: dict[str, Any]) -> None:
    expected = manifest["source_package"]
    actual_size = zip_path.stat().st_size
    actual_hash = sha256_file(zip_path)

    if actual_size != expected["bytes"]:
        raise ValueError(
            f"ZIP size mismatch: expected {expected['bytes']}, got {actual_size}"
        )
    if actual_hash != expected["sha256"]:
        raise ValueError(
            f"ZIP SHA-256 mismatch: expected {expected['sha256']}, got {actual_hash}"
        )


def ingest(zip_path: Path, repo_root: Path, write_package_copy: bool) -> None:
    manifest = load_manifest(repo_root)
    verify_package(zip_path, manifest)

    with zipfile.ZipFile(zip_path, "r") as archive:
        available = set(archive.namelist())

        for item in manifest["items"]:
            filename = item["filename"]
            target_path = repo_root / item["target_path"]

            if filename not in available:
                raise FileNotFoundError(f"Missing ZIP item: {filename}")

            data = archive.read(filename)
            actual_size = len(data)
            actual_hash = sha256_bytes(data)

            if actual_size != item["bytes"]:
                raise ValueError(
                    f"Size mismatch for {filename}: expected {item['bytes']}, got {actual_size}"
                )
            if actual_hash != item["sha256"]:
                raise ValueError(
                    f"SHA-256 mismatch for {filename}: expected {item['sha256']}, got {actual_hash}"
                )

            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(data)
            print(f"wrote {item['target_path']} ({actual_size} bytes)")

    if write_package_copy:
        package_target = repo_root / manifest["source_package"]["target_path"]
        package_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(zip_path, package_target)
        print(f"wrote {manifest['source_package']['target_path']} ({zip_path.stat().st_size} bytes)")

    print("archive ingestion complete; all hashes verified")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path, help="Path to Brain_Compilation_Full_Current_Thread_Package.zip")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root; defaults to current directory")
    parser.add_argument(
        "--skip-package-copy",
        action="store_true",
        help="Extract package contents but do not copy the ZIP itself into artifacts/",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    zip_path = args.zip_path.expanduser().resolve()
    repo_root = args.repo_root.expanduser().resolve()

    if not zip_path.exists():
        print(f"error: ZIP not found: {zip_path}", file=sys.stderr)
        return 2
    if not repo_root.exists():
        print(f"error: repo root not found: {repo_root}", file=sys.stderr)
        return 2

    try:
        ingest(zip_path, repo_root, write_package_copy=not args.skip_package_copy)
    except Exception as exc:  # noqa: BLE001 - command-line tool should show exact failure
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
