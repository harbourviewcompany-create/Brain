#!/usr/bin/env python3
"""Validate Brain PR body control sections.

The script reads the GitHub event payload from GITHUB_EVENT_PATH. It performs
no network calls and skips non-pull-request events so the same workflow can run
on push.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "docs/control/policy-registry.json"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize(text: str) -> str:
    return " ".join(text.lower().replace("_", " ").split())


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if event_name != "pull_request":
        print(f"Skipping PR body validation for event: {event_name or 'unknown'}")
        return 0

    if not event_path:
        fail("GITHUB_EVENT_PATH is not set")

    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Could not read GitHub event payload: {exc}")

    pull_request = event.get("pull_request") or {}
    body = pull_request.get("body") or ""
    if not body.strip():
        fail("Pull request body is empty")

    try:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Could not read policy registry: {exc}")

    normalized_body = normalize(body)
    required_sections = policy.get("required_pr_template_sections", [])
    missing_sections = [
        section for section in required_sections if normalize(section) not in normalized_body
    ]
    if missing_sections:
        fail("PR body missing required sections: " + ", ".join(missing_sections))

    required_terms = [
        "SOURCE",
        "APPROVED",
        "GO",
        "HOLD",
        "Tests",
        "External Actions",
        "Memory Writes",
        "Source Preservation",
        "Unresolved Gaps",
    ]
    missing_terms = [term for term in required_terms if term not in body]
    if missing_terms:
        fail("PR body missing required control terms: " + ", ".join(missing_terms))

    forbidden_placeholders = [
        "N/A because I did not check",
        "tests passed without evidence",
        "TODO before merge",
    ]
    present_forbidden = [term for term in forbidden_placeholders if term in body]
    if present_forbidden:
        fail("PR body contains unresolved placeholder/unsupported claim: " + ", ".join(present_forbidden))

    print("PR body validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
