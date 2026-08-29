from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VERCEL_CONFIG = REPO_ROOT / "apps/observatory/vercel.json"
PREVIEW_WORKFLOW = REPO_ROOT / ".github/workflows/deploy-vercel-preview.yml"


def _deployment_enabled(branch: str, rules: dict[str, bool]) -> bool:
    """Model Vercel deploymentEnabled semantics for the policy patterns used here.

    Vercel documents minimatch-style branch patterns, unspecified branches as enabled,
    and overlapping matches as enabled when any matching rule is true.
    """

    matches = [enabled for pattern, enabled in rules.items() if PurePosixPath(branch).match(pattern)]
    return any(matches) if matches else True


def test_vercel_git_deployment_policy_is_exactly_fail_closed() -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))
    assert config["framework"] == "nextjs"
    assert config["buildCommand"] == "npm run build"
    assert config["outputDirectory"] == ".next"
    assert config["git"]["deploymentEnabled"] == {
        "**": False,
        "main": True,
        "preview/*": True,
    }


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("main", True),
        ("preview/release-candidate", True),
        ("preview/qa-20260828", True),
        ("feat/living-cognitive-machine", False),
        ("fix/revenue-signal-schema", False),
        ("claude/repo-review-5vfhhw", False),
        ("dependabot/pip/fastapi-0.120.0", False),
        ("dependabot/github_actions/actions/checkout-5", False),
        ("docs/control-hardening", False),
        ("agent/runtime-review", False),
        ("future-prefix/unrecognized-work", False),
        ("unprefixed-unknown-branch", False),
        ("preview/team/nested-preview", False),
    ],
)
def test_branch_admission_contract(branch: str, expected: bool) -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))
    rules = config["git"]["deploymentEnabled"]
    assert _deployment_enabled(branch, rules) is expected


def test_manual_preview_workflow_deploys_directly_without_git_branch_staging() -> None:
    workflow = PREVIEW_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "pull_request:" not in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "persist-credentials: false" in workflow

    assert "git push" not in workflow
    assert "PREVIEW_BRANCH=" not in workflow
    assert "refs/heads/${PREVIEW_BRANCH}" not in workflow

    assert "VERCEL_ORG_ID: team_0rK4jTvMLlSufR0ZzX4LCKYi" in workflow
    assert "VERCEL_PROJECT_ID: prj_Fr14GlGBNeae7coqrnhgXteHC0jA" in workflow
    assert "secrets.VERCEL_TOKEN" in workflow
    assert "working-directory: apps/observatory" in workflow
    assert "vercel@latest pull" in workflow
    assert "--environment=preview" in workflow
    assert "vercel@latest build" in workflow
    assert "vercel@latest deploy" in workflow
    assert "--prebuilt" in workflow
    assert '--meta "brainPreviewName=${PREVIEW_NAME}"' in workflow
    assert '--meta "brainSourceRef=${SOURCE_REF}"' in workflow
    assert '--meta "brainSourceSha=${SOURCE_SHA}"' in workflow
