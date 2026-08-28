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
    require(policy["resource_creation"] == "existing_free_resources_only", "CI may use only existing free resources")
    providers = policy["providers"]
    require(providers["vercel"]["required_plan"] == "hobby", "Vercel must remain Hobby")
    require(providers["turso"]["required_plan"] == "free", "Turso must remain free tier")
    require(providers["turso"]["create_resources_from_ci"] is False, "CI cannot create Turso resources")
    require(providers["turso"]["paid_overage_allowed"] is False, "Turso overage must be disabled")
    require(providers["railway"]["production_dependency_allowed"] is False, "Railway cannot remain a production dependency")
    require(providers["railway"]["source_mutation_allowed"] is False, "Railway source mutation is forbidden")
    require(providers["railway"]["source_deletion_allowed"] is False, "Railway source deletion is forbidden")
    storage = policy["storage"]
    require(storage["canonical_events_may_be_silently_dropped"] is False, "canonical events cannot be silently dropped")
    require(int(storage["logical_budget_bytes"]) == 5 * 1024 * 1024 * 1024, "logical storage budget must remain 5 GiB")
    thresholds = storage["pressure_thresholds_percent"]
    require(int(thresholds["observe"]) == 60, "storage observation threshold must remain 60%")
    require(int(thresholds["compact"]) == 70, "storage compaction threshold must remain 70%")
    require(int(thresholds["prune_disposable_telemetry"]) == 80, "telemetry pruning threshold must remain 80%")
    require(int(thresholds["reject_noncanonical_growth"]) == 85, "optional-write refusal gate must remain 85%")
    require(policy["migration"]["workflow_trigger"] == "workflow_dispatch_only", "rescue must remain manual-only")
    require(policy["migration"]["verify_before_import"] is True, "migration verification must precede import")
    return policy


def validate_vercel_config(path: str, expected_ignore: str) -> None:
    config = json.loads(read(path))
    rules = config.get("git", {}).get("deploymentEnabled", {})
    require(rules.get("*") is False, f"{path}: all branches must default to no automatic deployment")
    require(rules.get("main") is True, f"{path}: main must be the only automatic deployment exception")
    require(config.get("ignoreCommand") == expected_ignore, f"{path}: ignored-build command mismatch")


def validate_vercel() -> None:
    validate_vercel_config("vercel.json", "bash scripts/vercel-ignore-build.sh")
    validate_vercel_config("apps/observatory/vercel.json", "bash ../../scripts/vercel-ignore-build.sh")
    script = read("scripts/vercel-ignore-build.sh")
    require("VERCEL_GIT_COMMIT_REF" in script, "ignored-build script must inspect branch")
    require("VERCEL_GIT_PREVIOUS_SHA" in script, "ignored-build script must inspect previous deployed SHA")
    require("exit 0" in script and "exit 1" in script, "ignored-build script must implement Vercel exit semantics")
    require('!= "main"' in script, "ignored-build script must skip non-main branches")
    for runtime_path in ("api/", "apps/api/", "apps/observatory/", "brain/"):
        require(runtime_path in script, f"ignored-build script must recognize runtime path {runtime_path}")


def workflow_trigger_block(text: str) -> str:
    match = re.search(r"(?ms)^on:\s*\n(?P<body>.*?)(?=^permissions:|^jobs:)", text)
    require(match is not None, "workflow must contain an explicit on: block")
    return match.group("body")


def validate_rescue_workflow() -> None:
    text = read(".github/workflows/railway-turso-rescue.yml")
    trigger = workflow_trigger_block(text)
    require(re.search(r"(?m)^\s{2}workflow_dispatch:\s*$", trigger) is not None, "Railway rescue must be workflow_dispatch-only")
    for forbidden_trigger in ("push:", "pull_request:", "schedule:", "workflow_run:"):
        require(forbidden_trigger not in trigger, f"Railway rescue cannot use {forbidden_trigger.rstrip(':')} trigger")
    require("secrets.RAILWAY_TOKEN" in text, "Railway rescue must use repository-secret RAILWAY_TOKEN")
    require("secrets.TURSO_DATABASE_URL" in text, "Turso destination URL must come from a secret")
    require("secrets.TURSO_AUTH_TOKEN" in text, "Turso auth token must come from a secret")
    require("import_to_turso" in text, "remote Turso import must be an explicit manual input")
    require("railway volume files" in text and "download" in text, "rescue must use Railway volume download")
    require("cp -a" in text, "rescue must recover only from a runner-local PGDATA copy")
    require("verify_event_replay_equivalence.py" in text, "rescue must verify canonical replay")
    lowered = text.lower()
    forbidden = (
        "railway volume delete",
        "railway volume files delete",
        "railway volume files upload",
        "railway volume files rename",
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
    require("railway" not in lowered, "postdeploy audit must have zero Railway dependency")
    required_contracts = (
        "health.status !== 'ok'",
        "health.database !== 'connected'",
        "health.persistence !== 'turso'",
        "storage.reachable !== true",
        "utilization >= 0.85",
        "Array.isArray(signals.items)",
        "organism payload missing",
    )
    for token in required_contracts:
        require(token in text, f"postdeploy audit missing hard contract: {token}")
    require("playwright" in lowered, "postdeploy audit must run a real browser")
    require("consoleerrors" in lowered and "pageerrors" in lowered and "servererrors" in lowered, "postdeploy audit must fail on browser/runtime errors")
    for viewport in ("desktop", "tablet", "mobile"):
        require(viewport in lowered, f"postdeploy audit must capture {viewport} browser evidence")
    require("production-${spec.name}.png" in text, "postdeploy screenshot contract missing")
    require("actions/upload-artifact@v4" in text, "postdeploy evidence must be uploaded")


def validate_runtime() -> None:
    entry = read("api/index.py")
    require("turso" in entry.lower(), "Vercel API entrypoint must bind Turso")
    require("BRAIN_INLINE_COGNITION" in entry, "Vercel entrypoint must disable inline cognition")
    policy = read("brain/storage_policy.py")
    require("5 * 1024 * 1024 * 1024" in policy, "logical storage budget must remain 5 GiB")
    require("REFUSE_OPTIONAL" in policy, "storage pressure must fail closed for optional growth")
    upstream = read("apps/observatory/src/lib/brain-upstream.ts")
    require("LIVE_RAILWAY_BASE" not in upstream, "Observatory BFF cannot retain Railway fallback")
    require(".railway.app" in upstream and "unsupported" in upstream.lower(), "BFF must reject Railway upstream configuration")
    require("BRAIN_API_URL" in upstream, "BFF must require an explicit zero-cost runtime origin")


def validate_protected_ci() -> None:
    workflow = read(".github/workflows/test.yml")
    required = (
        "python scripts/validate_zero_cost_runtime.py",
        "python -m compileall",
        "tests/test_turso_persistence.py",
        "tests/test_railway_turso_migration.py",
        "ruff check",
        "npm run verify",
        "zero-cost-migration-fixture",
        "railway_turso_migration.py convert",
        "verify_event_replay_equivalence.py",
        "migration-fixture-evidence",
    )
    for token in required:
        require(token in workflow, f"protected test workflow missing zero-cost gate: {token}")
    require("Tenant RLS release gate" in workflow, "PostgreSQL tenant-RLS regression gate must remain protected")
    control = read(".github/workflows/control-policy.yml")
    require("scripts/validate_zero_cost_runtime.py" in control, "control policy must execute zero-cost validator")


def main() -> None:
    validate_policy()
    validate_vercel()
    validate_rescue_workflow()
    validate_maintenance_workflow()
    validate_postdeploy()
    validate_runtime()
    validate_protected_ci()
    print("zero-cost runtime policy: PASS")


if __name__ == "__main__":
    main()
