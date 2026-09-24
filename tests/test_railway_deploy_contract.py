"""Regression guards for the retired Railway/Fly production boundary.

The canonical production architecture is Vercel + Turso/libSQL. Railway/Fly
deployment manifests are intentionally absent. PostgreSQL migration tooling may
remain only as an explicitly manual, read-only rescue source.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEGACY_HOSTING_ARTIFACTS = (
    "fly.toml",
    "railway.toml",
    "railway.brain-api-live.toml",
    "railway.worker.toml",
    "Dockerfile.railway",
    "Dockerfile.worker",
)


def test_retired_hosting_artifacts_are_absent() -> None:
    present = [name for name in LEGACY_HOSTING_ARTIFACTS if (ROOT / name).exists()]
    assert not present, f"retired hosted-production artifacts returned: {present}"


def test_canonical_container_is_the_only_root_production_container_contract() -> None:
    dockerfiles = sorted(ROOT.glob("Dockerfile*"))
    assert [path.name for path in dockerfiles] == ["Dockerfile"]


def test_manual_postgres_rescue_is_not_a_deployment_contract() -> None:
    workflow = ROOT / ".github/workflows/railway-turso-rescue.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8").lower()
    assert "workflow_dispatch:" in text
    for forbidden in (
        "railway up",
        "railway deploy",
        "railway redeploy",
        "fly deploy",
        "turso db create",
        "turso database create",
    ):
        assert forbidden not in text, f"rescue workflow contains deploy/create command: {forbidden}"


def test_zero_cost_policy_forbids_railway_production_dependency() -> None:
    policy = ROOT / "docs/control/zero_cost_policy.json"
    text = policy.read_text(encoding="utf-8")
    assert '"production_dependency_allowed": false' in text
