#!/usr/bin/env python3
"""Validate Brain control-layer enforcement files.

This script is intentionally dependency-free so GitHub Actions can run it in a
fresh Python environment. It validates repository control artifacts without
making any network calls or modifying files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "docs/control/policy-registry.json"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        fail(f"{path.relative_to(REPO_ROOT)} is not valid UTF-8: {exc}")


def read_json(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        fail(f"{path.relative_to(REPO_ROOT)} is invalid JSON: {exc}")


def require_files(paths: Iterable[str], category: str) -> None:
    path_list = list(paths)
    missing = [p for p in path_list if not (REPO_ROOT / p).is_file()]
    if missing:
        fail(f"Missing {category}: {', '.join(missing)}")
    print(f"OK: {category} present ({len(path_list)})")


def require_tokens(path: str, tokens: Iterable[str], category: str) -> None:
    file_path = REPO_ROOT / path
    content = read_text(file_path)
    missing = [token for token in tokens if token not in content]
    if missing:
        fail(f"{path} missing {category}: {', '.join(missing)}")
    print(f"OK: {path} contains required {category}")


def validate_policy_shape(policy: dict) -> None:
    required_top_level = [
        "policy_id",
        "status",
        "root_principle",
        "source_authority_labels",
        "go_hold_statuses",
        "required_control_files",
        "required_templates",
        "required_validators",
        "required_workflows",
        "required_pr_template_sections",
        "module_required_fields",
        "memory_write_required_fields",
        "external_action_required_fields",
        "archive_policy",
        "traceability_policy",
        "pr_body_policy",
        "forbidden_behaviors",
    ]
    missing = [key for key in required_top_level if key not in policy]
    if missing:
        fail(f"policy-registry.json missing keys: {', '.join(missing)}")

    expected_labels = {
        "SOURCE",
        "APPROVED",
        "PROPOSAL",
        "SPECULATIVE",
        "REVIEW-ONLY",
        "BLOCKED",
        "BUILD-READY",
    }
    actual_labels = set(policy["source_authority_labels"])
    if actual_labels != expected_labels:
        fail(
            "source_authority_labels mismatch: "
            f"expected {sorted(expected_labels)}, got {sorted(actual_labels)}"
        )

    expected_statuses = {"GO", "HOLD", "REVIEW", "BLOCKED"}
    actual_statuses = set(policy["go_hold_statuses"])
    if actual_statuses != expected_statuses:
        fail(
            "go_hold_statuses mismatch: "
            f"expected {sorted(expected_statuses)}, got {sorted(actual_statuses)}"
        )

    if not isinstance(policy.get("archive_policy"), dict):
        fail("archive_policy must be an object")
    if not isinstance(policy.get("traceability_policy"), dict):
        fail("traceability_policy must be an object")
    if not isinstance(policy.get("pr_body_policy"), dict):
        fail("pr_body_policy must be an object")

    print("OK: policy registry schema")


def validate_issue_template(path: str) -> None:
    require_tokens(
        path,
        ["name:", "about:", "title:", "labels:", "body:"],
        "issue-template structure",
    )
    expected_by_template = {
        ".github/ISSUE_TEMPLATE/blocked.yml": [
            "BLOCKED",
            "Source authority",
            "Unblock condition",
        ],
        ".github/ISSUE_TEMPLATE/build-ready.yml": [
            "BUILD-READY",
            "owner object",
            "runtime service",
            "GO/HOLD status",
        ],
        ".github/ISSUE_TEMPLATE/conflict.yml": [
            "CONFLICT",
            "Conflicting source records",
            "Resolution needed",
        ],
        ".github/ISSUE_TEMPLATE/source-record.yml": [
            "SOURCE",
            "Authority label",
            "Preserved content description",
        ],
    }
    require_tokens(
        path,
        expected_by_template.get(path, []),
        "template-specific control fields",
    )


#: Directory names whose contents are installed dependencies or local
#: environments rather than repository source.
_VENDORED_DIRECTORIES = frozenset(
    {"node_modules", "site-packages", ".venv", "venv", "build", "dist", ".next"}
)


def discover_code_modules(roots: Iterable[str], excluded_filenames: set[str]) -> set[str]:
    modules: set[str] = set()
    for root in roots:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            fail(f"Traceability root does not exist: {root}")
        for path in root_path.rglob("*.py"):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if path.name in excluded_filenames:
                continue
            if "/__pycache__/" in rel or rel.startswith("tests/"):
                continue
            # Third-party trees are not ours to trace. Without this, running
            # `npm install` in apps/observatory makes the validator demand a
            # traceability record for vendored Python inside node_modules.
            if any(part in _VENDORED_DIRECTORIES for part in path.parts):
                continue
            modules.add(rel)
    return modules


def _traceability_registries(policy: dict) -> list[tuple[str, dict]]:
    trace_policy = policy["traceability_policy"]
    registry_path = trace_policy.get("registry_path")
    if not registry_path or not (REPO_ROOT / registry_path).is_file():
        fail("traceability_policy.registry_path is missing or invalid")

    paths = [registry_path, *trace_policy.get("canonical_registry_extensions", [])]
    registries: list[tuple[str, dict]] = []
    for path in paths:
        candidate = REPO_ROOT / path
        if not candidate.is_file():
            fail(f"canonical traceability registry is missing: {path}")
        registries.append((path, read_json(candidate)))
    return registries


def validate_traceability_registry(policy: dict) -> None:
    trace_policy = policy["traceability_policy"]
    schema_path = trace_policy.get("schema_path")
    enforced_roots = trace_policy.get("enforced_code_roots", [])
    excluded_filenames = set(trace_policy.get("excluded_filenames", []))

    if not schema_path or not (REPO_ROOT / schema_path).is_file():
        fail("traceability_policy.schema_path is missing or invalid")

    registries = _traceability_registries(policy)
    required_keys = {
        "registry_id",
        "status",
        "sources",
        "requirements",
        "code_module_records",
    }

    sources: dict[str, dict] = {}
    requirements: dict[str, dict] = {}
    for registry_path, registry in registries:
        missing_keys = sorted(required_keys - set(registry))
        if missing_keys:
            fail(f"{registry_path} missing keys: {', '.join(missing_keys)}")
        for item in registry.get("sources", []):
            source_id = item.get("source_id")
            if source_id is None:
                fail(f"{registry_path} contains a source record without an ID")
            if source_id in sources and sources[source_id] != item:
                fail(f"Conflicting duplicate source traceability ID: {source_id}")
            sources[source_id] = item
        for item in registry.get("requirements", []):
            requirement_id = item.get("requirement_id")
            if requirement_id is None:
                fail(f"{registry_path} contains a requirement record without an ID")
            if requirement_id in requirements and requirements[requirement_id] != item:
                fail(f"Conflicting duplicate requirement traceability ID: {requirement_id}")
            requirements[requirement_id] = item

    for requirement_id, requirement in requirements.items():
        for source_id in requirement.get("source_ids", []):
            if source_id not in sources:
                fail(f"Requirement {requirement_id} references missing source {source_id}")

    required_record_fields = [
        "record_id",
        "paths",
        "classification",
        "go_hold_status",
        "source_ids",
        "requirement_ids",
        "owner_object",
        "schema",
        "runtime_service",
        "state_machine",
        "fixtures",
        "tests",
        "acceptance_criteria",
        "audit_events",
        "source_preservation",
        "unresolved_gaps",
    ]

    covered_paths: set[str] = set()
    record_ids: set[str] = set()
    for registry_path, registry in registries:
        for record in registry.get("code_module_records", []):
            record_id = record.get("record_id", "<missing record_id>")
            if record_id in record_ids:
                fail(f"Duplicate traceability record ID: {record_id}")
            record_ids.add(record_id)
            missing_fields = [
                field
                for field in required_record_fields
                if field not in record or record[field] in ("", [], None)
            ]
            if missing_fields:
                fail(
                    f"Traceability record {record_id} in {registry_path} "
                    f"missing fields: {', '.join(missing_fields)}"
                )

            if record["classification"] not in policy["source_authority_labels"]:
                fail(f"{record_id} has invalid classification: {record['classification']}")
            if record["go_hold_status"] not in policy["go_hold_statuses"]:
                fail(f"{record_id} has invalid GO/HOLD status: {record['go_hold_status']}")

            for source_id in record.get("source_ids", []):
                if source_id not in sources:
                    fail(f"{record_id} references missing source {source_id}")
            for requirement_id in record.get("requirement_ids", []):
                if requirement_id not in requirements:
                    fail(f"{record_id} references missing requirement {requirement_id}")
            for module_path in record["paths"]:
                if not (REPO_ROOT / module_path).is_file():
                    fail(f"{record_id} references missing code path {module_path}")
                covered_paths.add(module_path)

    discovered = discover_code_modules(enforced_roots, excluded_filenames)
    missing_records = sorted(discovered - covered_paths)
    if missing_records:
        fail("Code modules missing traceability records: " + ", ".join(missing_records))

    unknown_records = sorted(covered_paths - discovered)
    if unknown_records:
        warn(
            "Traceability records exist for non-discovered code paths: "
            + ", ".join(unknown_records)
        )

    print(
        "OK: canonical traceability registries cover enforced code modules "
        f"({len(discovered)} modules across {len(registries)} registries)"
    )


def main() -> int:
    if not POLICY_PATH.is_file():
        fail("docs/control/policy-registry.json is missing")

    policy = read_json(POLICY_PATH)
    validate_policy_shape(policy)

    require_files(policy["required_control_files"], "control files")
    require_files(policy["required_templates"], "GitHub templates")
    require_files(policy["required_validators"], "validator scripts")
    require_files(policy["required_workflows"], "GitHub Actions workflows")

    require_tokens(
        ".github/pull_request_template.md",
        policy["required_pr_template_sections"],
        "PR sections",
    )

    for template in policy["required_templates"]:
        if template.endswith("pull_request_template.md"):
            continue
        validate_issue_template(template)

    require_tokens(
        "docs/control/brain-build-rules.md",
        ["Tyler", "preserve", "Classify", "GO/HOLD"],
        "root control concepts",
    )
    require_tokens(
        "docs/control/definition-of-done.md",
        policy["module_required_fields"],
        "module completion fields",
    )
    require_tokens(
        "docs/control/acceptance-evidence-template.md",
        [
            "tests_run",
            "external_actions_taken",
            "memory_writes_made",
            "source_preservation_statement",
        ],
        "acceptance evidence fields",
    )

    archive_policy = policy["archive_policy"]
    archive_manifest = archive_policy.get("manifest_path")
    if not archive_manifest or not (REPO_ROOT / archive_manifest).is_file():
        fail("archive_policy.manifest_path is missing or does not point to a file")

    validate_traceability_registry(policy)

    if policy["archive_policy"].get("allow_pending_assets") is True:
        warn(
            "archive assets may remain pending; "
            "validate_archive_manifest.py enforces manifest integrity"
        )

    print("Brain control layer validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
