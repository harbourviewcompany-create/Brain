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
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "harbourviewcompany-create/Brain")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MAIN_BRANCH = os.environ.get("BRAIN_MAIN_BRANCH", "main")

REQUIRED_STATUS_CHECKS = {"Brain Control Policy", "test"}
EXPECTED_ARCHIVE_PATHS = [
    "docs/archive/Brain_Compilation_Full_Current_Thread.docx",
    "docs/archive/Brain_Compilation_Full_Current_Thread.md",
    "docs/archive/source/Pasted text.txt",
    "docs/archive/visuals/step_by_step_process_overview.png",
    "docs/archive/visuals/brain_functions_vs._real_brain_anatomy.png",
    "docs/archive/visuals/a_high_detail_infographic_poster_on_a_dark_black_t.png",
    "docs/archive/visuals/brain_vs_ai_a_comparative_overview.png",
    "docs/archive/visuals/brain_architecture_vs_generic_ai_comparison.png",
    "docs/archive/visuals/comparing_ai_and_brain_architectures.png",
    "artifacts/Brain_Compilation_Full_Current_Thread_Package.zip",
]


def error(message: str) -> None:
    print(f"::error::{message}")


def warning(message: str) -> None:
    print(f"::warning::{message}")


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
    gaps: list[str] = []
    manifest_path = ROOT / "docs" / "archive" / "archive_manifest.json"
    if not manifest_path.is_file():
        return ["archive manifest is missing"]

    missing = [path for path in EXPECTED_ARCHIVE_PATHS if not (ROOT / path).is_file()]
    if missing:
        gaps.append("archive asset file bytes missing: " + ", ".join(missing))

    return gaps


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
