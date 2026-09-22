#!/usr/bin/env python3
"""Audit repository hardening gaps that cannot be fixed by normal repo files.

This script is intentionally read-only. It checks whether GitHub branch
protection is configured for main and whether the real archive file bytes are
present in the checkout. It does not mutate GitHub settings, upload files, or
create placeholders.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "harbourviewcompany-create/Brain")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MAIN_BRANCH = os.environ.get("BRAIN_MAIN_BRANCH", "main")

# NOTE: these must be the job-level `name:` fields from the workflow files
# (what GitHub actually records as the status-check context), not the
# top-level workflow `name:` field. See
# .github/workflows/control-policy.yml -> jobs.control-policy.name and
# .github/workflows/test.yml -> jobs.test.name.
# tests/test_check_repository_hardening.py cross-checks this constant
# against those files directly so a future workflow rename can't silently
# reintroduce this bug.
REQUIRED_STATUS_CHECKS = {"Validate Brain control policy", "test"}





def error(message: str) -> None:
    print(f"::error::{message}")


def request_json(url: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "brain-repository-hardening-audit",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API request failed: {exc.code} {url}\n{body}") from exc


def check_branch_protection() -> list[str]:
    gaps: list[str] = []
    branch_url = f"https://api.github.com/repos/{REPOSITORY}/branches/{MAIN_BRANCH}"
    branch = request_json(branch_url)

    if not branch.get("protected"):
        gaps.append(f"{MAIN_BRANCH} branch protection is disabled")
        return gaps

    protection = branch.get("protection", {}) or {}
    required = protection.get("required_status_checks", {}) or {}
    checks = {item.get("context") or item.get("app_id") for item in required.get("checks", [])}
    contexts = set(required.get("contexts", []) or [])
    normalized = {str(item) for item in checks.union(contexts) if item}

    missing = sorted(REQUIRED_STATUS_CHECKS - normalized)
    if missing:
        gaps.append("required status checks missing from branch protection: " + ", ".join(missing))

    return gaps


def check_archive_assets() -> list[str]:
    manifest_path = ROOT / "docs" / "archive" / "archive_manifest.json"
    if not manifest_path.is_file():
        return ["archive manifest is missing"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"archive manifest cannot be read: {exc}"]

    required_top_level = {"archive_id", "title", "status", "rule", "source_package", "items"}
    if not required_top_level.issubset(manifest):
        missing_keys = sorted(required_top_level - set(manifest))
        return ["archive manifest missing required keys: " + ", ".join(missing_keys)]

    source_package = manifest["source_package"]
    items = manifest["items"]
    if not isinstance(source_package, dict):
        return ["archive manifest source_package must be an object"]
    if not isinstance(items, list) or not items:
        return ["archive manifest items must be a non-empty list"]

    declared: list[str] = []
    target_values = [("source_package.target_path", source_package.get("target_path"))]
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return [f"archive manifest items[{index}] must be an object"]
        if item.get("required"):
            target_values.append((f"items[{index}].target_path", item.get("target_path")))

    for field, value in target_values:
        if not isinstance(value, str) or not value.strip():
            return [f"archive manifest {field} must be a non-empty repo-relative path"]
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            return [f"archive manifest {field} must be a safe repo-relative path: {value}"]
        declared.append(value)

    missing = sorted({path for path in declared if not (ROOT / path).is_file()})
    if missing:
        return ["archive asset file bytes missing: " + ", ".join(missing)]
    return []

def main() -> int:
    gaps = []
    gaps.extend(check_branch_protection())
    gaps.extend(check_archive_assets())

    if gaps:
        for gap in gaps:
            error(gap)
        print("Repository hardening audit: BLOCKED")
        print("Tracked issues: #51 branch protection, #52 archive file-byte upload")
        return 1

    print("Repository hardening audit: GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
