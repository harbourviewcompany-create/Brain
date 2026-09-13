"""The cutover gate must stay satisfiable, and the rescue must target the real volume.

These pin two failures that are invisible to every other check. A cutover gate
that requires an impossible precondition still reads as a safety control, and a
rescue workflow with the wrong volume id still reads as configured -- it just
exits before downloading anything.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "docs/control/zero_cost_policy.json").read_text(encoding="utf-8"))
RUNTIME_DOC = (ROOT / "docs/control/ZERO_COST_RUNTIME.md").read_text(encoding="utf-8")
RESCUE = yaml.safe_load((ROOT / ".github/workflows/railway-turso-rescue.yml").read_text(encoding="utf-8"))
# YAML 1.1 resolves the bare key `on` to the boolean True, so a workflow's trigger
# block is not reachable under the string "on". Look both up rather than assuming.
RESCUE_TRIGGERS = RESCUE.get("on", RESCUE.get(True))

#: The volume actually attached to the Railway Postgres service. The workflow
#: verifies this id against `railway volume list` and exits when it is absent,
#: so a stale default fails the rescue's own gate before any download.
LIVE_VOLUME_ID = "8c85b856-4358-49a8-82f9-8e8bdd648f07"


def test_cutover_admits_a_path_that_does_not_depend_on_the_source():
    """A gate requiring a readable source is unsatisfiable once the source lapses."""

    assert POLICY["cutover"]["admissible_paths"] == ["migrated", "clean_start"]


def test_clean_start_cannot_lose_data_silently():
    """Accepting loss is a decision; discovering it later is a defect."""

    cutover = POLICY["cutover"]
    assert cutover["silent_data_loss_allowed"] is False
    assert cutover["clean_start_requires_explicit_data_loss_acknowledgement"] is True
    assert cutover["clean_start_requires_recorded_source_evidence"] is True


def test_clean_start_cannot_be_reached_by_paying_to_recover_the_source():
    """The zero-dollar invariant is the reason Path B exists; it must not dissolve it."""

    assert POLICY["cutover"]["paid_plan_to_recover_source_allowed"] is False
    assert POLICY["monthly_paid_budget_usd"] == 0


def test_a_migrated_cutover_still_requires_a_verified_rescue():
    """Path B must not weaken Path A."""

    assert POLICY["cutover"]["migrated_requires_verified_rescue"] is True
    assert POLICY["migration"]["verify_before_import"] is True


def test_the_rescue_targets_the_volume_that_actually_exists():
    """The previous default named a volume absent from the project."""

    default = RESCUE_TRIGGERS["workflow_dispatch"]["inputs"]["volume_id"]["default"]
    assert default == LIVE_VOLUME_ID


def test_the_runtime_doc_records_why_the_source_is_unrecoverable():
    """Path B is only usable if the evidence it demands is actually written down."""

    assert "Your trial has expired" in RUNTIME_DOC
    assert "8c85b856-4358-49a8-82f9-8e8bdd648f07" in RUNTIME_DOC


def test_the_deployment_topology_records_that_the_api_needs_its_own_build_root():
    """The Observatory building alone is the failure that made the outage invisible."""

    assert "Deployment topology" in RUNTIME_DOC
    assert "api/index.py" in RUNTIME_DOC
    assert "BRAIN_API_URL" in RUNTIME_DOC


# ---------------------------------------------------------------------------
# The hourly maintenance job must not be permanently red before cutover.
#
# `zero-cost-maintenance.yml` runs every hour against the Turso destination.
# That destination does not exist until the production cutover, so the job
# used to fail on every single run. A control that is always red is not a
# control -- it is noise that trains readers to ignore the one run that
# matters. These tests execute the gate script itself rather than matching
# strings, so a future edit that reintroduces the hard failure is caught.
# ---------------------------------------------------------------------------

MAINTENANCE = yaml.safe_load(
    (ROOT / ".github/workflows/zero-cost-maintenance.yml").read_text(encoding="utf-8")
)
MAINTENANCE_STEPS = MAINTENANCE["jobs"]["maintain"]["steps"]


def _step(step_id: str) -> dict:
    for step in MAINTENANCE_STEPS:
        if step.get("id") == step_id:
            return step
    raise AssertionError(f"no step with id {step_id!r} in zero-cost-maintenance.yml")


def _run_destination_gate(tmp_path, **env: str):
    """Execute the destination gate exactly as the workflow does."""

    import subprocess

    output = tmp_path / "github_output"
    output.touch()
    result = subprocess.run(
        ["bash", "-c", _step("destination")["run"]],
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ["PATH"],
            "GITHUB_OUTPUT": str(output),
            "TURSO_DATABASE_URL": "",
            "TURSO_AUTH_TOKEN": "",
            **env,
        },
    )
    return result, output.read_text(encoding="utf-8")


def test_maintenance_skips_cleanly_when_the_destination_does_not_exist_yet(tmp_path):
    """Before cutover there is nothing to maintain; that is not a failure."""

    result, output = _run_destination_gate(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "configured=false" in output
    assert "configured=true" not in output


def test_maintenance_still_fails_on_a_half_configured_destination(tmp_path):
    """One secret without the other is a real misconfiguration, not a skip."""

    url_only, _ = _run_destination_gate(tmp_path, TURSO_DATABASE_URL="libsql://brain.turso.io")
    assert url_only.returncode != 0
    assert "TURSO_AUTH_TOKEN" in url_only.stdout + url_only.stderr

    token_only, _ = _run_destination_gate(tmp_path, TURSO_AUTH_TOKEN="token")
    assert token_only.returncode != 0
    assert "TURSO_DATABASE_URL" in token_only.stdout + token_only.stderr


def test_maintenance_still_rejects_a_destination_that_is_not_remote(tmp_path):
    """A local file destination would silently maintain the wrong database."""

    result, _ = _run_destination_gate(
        tmp_path, TURSO_DATABASE_URL="file:local.db", TURSO_AUTH_TOKEN="token"
    )

    assert result.returncode != 0
    assert "remote libSQL/Turso database" in result.stdout + result.stderr


def test_a_configured_destination_still_runs_maintenance(tmp_path):
    """The skip must not swallow the real run once cutover happens."""

    result, output = _run_destination_gate(
        tmp_path, TURSO_DATABASE_URL="libsql://brain.turso.io", TURSO_AUTH_TOKEN="token"
    )

    assert result.returncode == 0, result.stderr
    assert "configured=true" in output

    run_step = next(s for s in MAINTENANCE_STEPS if "zero_cost_maintenance.py" in s.get("run", ""))
    assert run_step["if"] == "steps.destination.outputs.configured == 'true'"
