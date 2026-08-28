from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs/control/zero_cost_policy.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"zero-cost policy violation: {message}")


def read(path: str) -> str:
    target = ROOT / path
    require(target.is_file(), f"required file missing: {path}")
    return target.read_text(encoding="utf-8")


def validate_policy() -> dict:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    require(policy["monthly_paid_budget_usd"] == 0, "monthly paid budget must be zero")
    require(policy["paid_overage_allowed"] is False, "paid overage must be disabled")
    require(
        policy["resource_creation"] == "existing_free_resources_only",
        "CI may use only existing free resources",
    )
    providers = policy["providers"]
    require(providers["vercel"]["required_plan"] == "hobby", "Vercel must remain Hobby")
    require(providers["turso"]["required_plan"] == "free", "Turso must remain free tier")
    require(providers["turso"]["create_resources_from_ci"] is False, "CI cannot create Turso resources")
    require(providers["turso"]["paid_overage_allowed"] is False, "Turso overage must be disabled")
    require(providers["railway"]["production_dependency_allowed"] is False, "Railway cannot remain a production dependency")
    require(providers["railway"]["source_mutation_allowed"] is False, "Railway source mutation is forbidden")
    require(providers["railway"]["source_deletion_allowed"] is False, "Railway source deletion is forbidden")
    require(policy["storage"]["canonical_events_may_be_silently_dropped"] is False, "canonical events cannot be silently dropped")
    require(policy["migration"]["workflow_trigger"] == "workflow_dispatch_only", "rescue must remain manual-only")
    require(policy["migration"]["verify_before_import"] is True, "migration verification must precede import")
    return policy


def validate_vercel() -> None:
    config = json.loads(read("vercel.json"))
    rules = config.get("git", {}).get("deploymentEnabled", {})
    require(rules.get("*") is False, "all branches must default to no automatic deployment")
    require(rules.get("main") is True, "main must be the only automatic deployment exception")
    require(config.get("ignoreCommand") == "bash scripts/vercel-ignore-build.sh", "Vercel must use repository ignored-build control")
    script = read("scripts/vercel-ignore-build.sh")
    require('VERCEL_GIT_COMMIT_REF' in script, "ignored-build script must inspect branch")
    require('VERCEL_GIT_PREVIOUS_SHA' in script, "ignored-build script must inspect previous deployed SHA")
    require('exit 0' in script and 'exit 1' in script, "ignored-build script must implement Vercel exit semantics")
    require('!= "main"' in script, "ignored-build script must skip non-main branches")


def workflow_trigger_block(text: str) -> str:
    match = re.search(r"(?ms)^on:\s*\n(?P<body>.*?)(?=^permissions:|^jobs:)", text)
    require(match is not None, "workflow must contain an explicit on: block")
    return match.group("body")


def validate_rescue_workflow() -> None:
    path = ".github/workflows/railway-turso-rescue.yml"
    text = read(path)
    trigger = workflow_trigger_block(text)
    require(re.search(r"(?m)^\s{2}workflow_dispatch:\s*$", trigger) is not None, "Railway rescue must be workflow_dispatch-only")
    for forbidden_trigger in ("push:", "pull_request:", "schedule:", "workflow_run:"):
        require(forbidden_trigger not in trigger, f"Railway rescue cannot use {forbidden_trigger.rstrip(':')} trigger")
    require("secrets.RAILWAY_TOKEN" in text, "Railway rescue must use repository-secret RAILWAY_TOKEN")
    require("secrets.TURSO_DATABASE_URL" in text, "Turso destination URL must come from a secret")
    require("secrets.TURSO_AUTH_TOKEN" in text, "Turso auth token must come from a secret")
    require("import_to_turso" in text, "remote Turso import must be an explicit manual input")
    require("verify" in text.lower(), "rescue workflow must contain verification gates")
    lowered = text.lower()
    forbidden = (
        "railway volume delete",
        "railway service delete",
        "railway project delete",
        "railway delete",
        "turso db create",
        "turso database create",
        "turso group create",
        "turso plan",
        "turso billing",
    )
    for token in forbidden:
        require(token not in lowered, f"rescue workflow contains forbidden paid/destructive command: {token}")


def validate_maintenance_workflow() -> None:
    text = read(".github/workflows/zero-cost-maintenance.yml")
    require("schedule:" in workflow_trigger_block(text), "maintenance must be scheduled")
    require("concurrency:" in text, "maintenance must have concurrency protection")
    require("cancel-in-progress: false" in text, "maintenance runs must not overlap by cancellation/restart")
    require("BRAIN_MAINTENANCE_MAX_ITEMS" in text, "maintenance cognition must be bounded")
    require("BRAIN_MAINTENANCE_MAX_EVENTS" in text, "maintenance compaction must be bounded")
    require("TURSO_DATABASE_URL" in text and "TURSO_AUTH_TOKEN" in text, "maintenance must use Turso persistence")


def validate_postdeploy() -> None:
    text = read(".github/workflows/postdeploy-observatory-audit.yml")
    lowered = text.lower()
    require("brain-api-live-production.up.railway.app" not in lowered, "postdeploy audit still calls Railway")
    require("persistence" in lowered and "turso" in lowered, "postdeploy audit must require persistence=turso")
    require("storage" in lowered and "pressure" in lowered, "postdeploy audit must inspect storage pressure")
    for viewport in ("desktop", "tablet", "mobile"):
        require(viewport in lowered, f"postdeploy audit must capture {viewport} browser evidence")


def validate_runtime() -> None:
    entry = read("api/index.py")
    require("turso" in entry.lower(), "Vercel API entrypoint must bind Turso")
    require("BRAIN_INLINE_COGNITION" in entry, "Vercel entrypoint must disable inline cognition")
    policy = read("brain/storage_policy.py")
    require("5 * 1024 * 1024 * 1024" in policy, "logical storage budget must remain 5 GiB")
    require("REFUSE_OPTIONAL" in policy, "storage pressure must fail closed for optional growth")


def main() -> None:
    validate_policy()
    validate_vercel()
    validate_rescue_workflow()
    validate_maintenance_workflow()
    validate_postdeploy()
    validate_runtime()
    print("zero-cost runtime policy: PASS")


if __name__ == "__main__":
    main()
