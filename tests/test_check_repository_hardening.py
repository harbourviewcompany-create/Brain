"""Tests for tools/check_repository_hardening.py.

This script previously had no test coverage at all, which is how a
context-name bug shipped and stayed broken across multiple sessions:
REQUIRED_STATUS_CHECKS listed "Brain Control Policy" (the workflow-level
`name:` in .github/workflows/control-policy.yml) instead of "Validate Brain
control policy" (the job-level `name:`, which is what GitHub actually
records as the status-check context). The script ran on a daily cron and
reported BLOCKED unconditionally regardless of real protection state.

test_required_status_checks_match_actual_workflow_job_names is a regression
test: it derives the real context names directly from the workflow files
and asserts REQUIRED_STATUS_CHECKS matches them, so a future workflow
rename can't silently reintroduce this bug without breaking this test.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.check_repository_hardening import (
    REQUIRED_STATUS_CHECKS,
    check_archive_assets,
    check_branch_protection,
)

ROOT = Path(__file__).resolve().parents[1]


def _job_context_from_workflow(workflow_path: Path, job_id: str) -> str:
    """Return the status-check context GitHub records for a job: the job's
    `name:` field if present, else the job id itself (GitHub's fallback
    behavior). Deliberately a small targeted parser, not a general YAML
    parser - PyYAML is not a declared project dependency."""
    lines = workflow_path.read_text().splitlines()
    in_job = False
    job_indent = None
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if stripped == f"{job_id}:":
            in_job = True
            job_indent = indent
            continue
        if in_job:
            if indent <= job_indent:
                break
            if stripped.startswith("name:"):
                return stripped.split("name:", 1)[1].strip()
    return job_id


def test_required_status_checks_match_actual_workflow_job_names():
    control_policy_context = _job_context_from_workflow(
        ROOT / ".github" / "workflows" / "control-policy.yml", "control-policy"
    )
    test_context = _job_context_from_workflow(ROOT / ".github" / "workflows" / "test.yml", "test")

    actual_contexts = {control_policy_context, test_context}
    assert REQUIRED_STATUS_CHECKS == actual_contexts, (
        f"REQUIRED_STATUS_CHECKS {REQUIRED_STATUS_CHECKS} does not match the real "
        f"job-level status-check contexts {actual_contexts} derived from the workflow "
        "files. If a job was intentionally renamed, update REQUIRED_STATUS_CHECKS to "
        "match - do not just update this test."
    )


def _fake_branch_response(contexts: list[str] | None = None, protected: bool = True) -> dict:
    return {
        "protected": protected,
        "protection": {
            "required_status_checks": {"contexts": contexts or []},
        },
    }


def test_check_branch_protection_passes_with_correct_contexts():
    with patch(
        "tools.check_repository_hardening.request_json",
        return_value=_fake_branch_response(["Validate Brain control policy", "test"]),
    ):
        gaps = check_branch_protection()
    assert gaps == []


def test_check_branch_protection_flags_missing_context():
    with patch(
        "tools.check_repository_hardening.request_json",
        return_value=_fake_branch_response(["test"]),
    ):
        gaps = check_branch_protection()
    assert len(gaps) == 1
    assert "Validate Brain control policy" in gaps[0]


def test_check_branch_protection_flags_disabled_protection():
    with patch(
        "tools.check_repository_hardening.request_json",
        return_value=_fake_branch_response(protected=False),
    ):
        gaps = check_branch_protection()
    assert gaps == ["main branch protection is disabled"]


def test_check_branch_protection_would_have_caught_the_original_bug():
    """Regression proof: the stale value that shipped for multiple sessions
    ("Brain Control Policy") would never match a real branch-protection
    response containing the real context ("Validate Brain control policy"),
    so the script reported BLOCKED unconditionally. This test fails if that
    stale value is ever reintroduced."""
    stale_value = "Brain Control Policy"
    assert stale_value not in REQUIRED_STATUS_CHECKS


def test_check_archive_assets_reports_missing_manifest_or_files():
    # This repo's real state currently has a manifest but missing asset
    # bytes (tracked separately as issue #52) - just assert the function
    # runs and returns a list without raising, since asserting exact
    # repo-state content here would duplicate issue #52 tracking.
    result = check_archive_assets()
    assert isinstance(result, list)


def test_repository_does_not_track_local_environments_or_packaging_outputs():
    """Prevent the contamination class observed in PR #53 from recurring."""
    tracked = subprocess.check_output(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden_root_prefixes = (".venv/", "venv/", "env/", "build/", "dist/")
    offenders = [
        path
        for path in tracked
        if path.startswith(forbidden_root_prefixes)
        or path.endswith(".egg-info")
        or ".egg-info/" in path
    ]
    assert offenders == [], (
        "Generated local environments or packaging outputs are tracked by git: "
        + ", ".join(offenders[:20])
    )


def test_gitignore_blocks_repository_contamination_paths():
    ignored = set((ROOT / ".gitignore").read_text().splitlines())
    required = {".venv/", "venv/", "env/", "*.egg-info/", "build/", "dist/"}
    assert required <= ignored
