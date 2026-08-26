#!/usr/bin/env python3
"""Validate Brain agent-control files and implementation evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/agent-control/AGENT_BUILD_MASTER.md",
    "docs/agent-control/AGENT_RULES.md",
    "docs/agent-control/AGENT_TASK_QUEUE.md",
    "docs/agent-control/AGENT_FILE_MAP.md",
    "docs/agent-control/AGENT_PROMPT_PACK.md",
    "docs/agent-control/AGENT_ACCEPTANCE_PROTOCOL.md",
    "docs/agent-control/AGENT_HANDOFF_TEMPLATE.md",
    "docs/agent-control/ISSUE_GENERATION.md",
    "docs/agent-control/agent-control.json",
    "docs/agent-control/task-queue.json",
    "docs/spec/BRAIN_CANONICAL_SCOPE.md",
    "docs/spec/BRAIN_MODULE_MANIFEST.md",
    "docs/spec/BRAIN_FORMULA_REGISTRY.md",
    "docs/spec/BRAIN_SCHEMA_REGISTRY.md",
    "docs/spec/BRAIN_STATE_MACHINES.md",
    "docs/spec/BRAIN_RUNTIME_LOOPS.md",
    "docs/spec/BRAIN_FIXTURE_LIBRARY.md",
    "docs/spec/BRAIN_ACCEPTANCE_MATRIX.md",
    "docs/spec/BRAIN_SOURCE_TO_BUILD_TRACEABILITY.md",
    "docs/spec/module-manifest.json",
    "docs/spec/formula-registry.json",
    "docs/spec/schema-registry.json",
    "docs/spec/acceptance-matrix.json",
    "docs/spec/source-to-build-traceability.json",
    "docs/control/go_hold_issue_reconciliation.json",
    "brain/schemas.py",
    "brain/formulas.py",
    "brain/replay.py",
    "brain/contradiction_queue.py",
]

REQUIRED_FIXTURES = [
    "tests/fixtures/brain/source_signal_evidence_belief.json",
    "tests/fixtures/brain/formula_run_attention_reward.json",
    "tests/fixtures/brain/approval_gate_external_action.json",
    "tests/fixtures/brain/outcome_reward_pain_learning.json",
    "tests/fixtures/brain/contradiction_review.json",
    "tests/fixtures/brain/acceptance_gate_go_hold.json",
    "tests/fixtures/brain/capital_starvation_cycle.json",
    "tests/fixtures/brain/learning_generalization_and_consolidation.json",
]

VALID_TASK_STATUSES = {"implemented", "in_progress", "planned", "blocked"}

REQUIRED_REPORTS = [
    "reports/acceptance/AGENT-001-executable-schemas.json",
    "reports/acceptance/AGENT-002-formula-runtime.json",
    "reports/acceptance/AGENT-003-replay-harness.json",
    "reports/acceptance/AGENT-004-contradiction-review.json",
    "reports/acceptance/AGENT-005-ci-acceptance-gate.json",
    "reports/acceptance/AGENT-006-source-to-build-traceability.json",
    "reports/go-hold/GO-HOLD-SUMMARY.json",
]


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_go_hold_issue_reconciliation() -> None:
    data = load_json("docs/control/go_hold_issue_reconciliation.json")
    issues = {int(issue["issue_number"]): issue for issue in data.get("issues", [])}
    failures: list[str] = []
    for report in data.get("reports", []):
        if report.get("verdict") != "GO":
            continue
        for number in report.get("issue_numbers", []):
            issue = issues.get(int(number))
            if issue is None:
                failures.append(f"GO report references missing issue #{number}")
                continue
            if issue.get("issue_state") != "closed" and not issue.get("explicit_open_reason"):
                failures.append(f"GO report references open issue #{number} without explicit reason")
            if not issue.get("evidence_refs") or not report.get("evidence_refs"):
                failures.append(f"GO report or issue #{number} lacks evidence refs")
    require(not failures, f"GO/HOLD issue reconciliation failed: {failures}")


def validate_task_statuses(tasks: list[dict]) -> None:
    for task in tasks:
        require(
            task["status"] in VALID_TASK_STATUSES,
            f"Task has unrecognized status (expected one of {sorted(VALID_TASK_STATUSES)}): {task}",
        )


def implemented_tasks_of(tasks: list[dict]) -> list[dict]:
    return [task for task in tasks if task["status"] == "implemented"]


def validate_implemented_fixtures_materialized(tasks: list[dict], fixture_ids: set[str]) -> None:
    # Only tasks actually claiming to be done need materialized evidence.
    # A queue that can only represent finished work isn't a queue, it's a
    # changelog. Backlog statuses may reference fixtures/tests that don't
    # exist yet -- that's the point of tracking planned work honestly
    # instead of only registering it after the fact.
    referenced: set[str] = set()
    for task in implemented_tasks_of(tasks):
        referenced.update(task.get("required_fixtures", []))
    referenced.discard("all_required_fixture_files")
    referenced.discard("none")
    missing_referenced = sorted(referenced - fixture_ids)
    require(
        not missing_referenced,
        f"Task marked implemented but references unmaterialized fixtures: {missing_referenced}",
    )


def main() -> None:
    required_paths = REQUIRED_FILES + REQUIRED_FIXTURES + REQUIRED_REPORTS
    missing = [path for path in required_paths if not (ROOT / path).exists()]
    require(not missing, f"Missing required Brain agent-control artifacts: {missing}")

    task_queue = load_json("docs/agent-control/task-queue.json")
    tasks = task_queue.get("tickets", [])
    require(tasks, "task-queue.json must contain tickets")
    for task in tasks:
        for field in [
            "ticket_id",
            "issue_number",
            "issue_url",
            "objective",
            "files_to_create_or_modify",
            "required_tests",
            "required_fixtures",
            "acceptance_criteria",
            "go_hold_condition",
            "status",
        ]:
            require(field in task, f"Task missing {field}: {task}")
    validate_task_statuses(tasks)

    acceptance = load_json("docs/spec/acceptance-matrix.json")
    rules = acceptance.get("rules", [])
    require(rules, "acceptance-matrix.json must contain rules")
    for rule in rules:
        require(rule.get("go_hold_status") == "GO", f"Acceptance rule is not GO: {rule}")
        require(rule.get("required_evidence"), f"Acceptance rule missing evidence: {rule}")

    traceability = load_json("docs/spec/source-to-build-traceability.json")
    rows = traceability.get("traceability", [])
    require(rows, "source-to-build traceability must contain rows")
    required_row_fields = [
        "concept_family",
        "source_section",
        "module",
        "schema",
        "service",
        "formula",
        "test",
        "fixture",
        "dashboard",
        "acceptance_rule",
    ]
    for row in rows:
        for field in required_row_fields:
            require(row.get(field), f"Traceability row missing {field}: {row}")

    fixture_ids = set()
    for fixture in REQUIRED_FIXTURES:
        data = load_json(fixture)
        require(data.get("fixture_id"), f"Fixture missing fixture_id: {fixture}")
        require(data.get("scenario"), f"Fixture missing scenario: {fixture}")
        require("expected" in data, f"Fixture missing expected block: {fixture}")
        fixture_ids.add(data["fixture_id"])

    validate_implemented_fixtures_materialized(tasks, fixture_ids)

    for report_path in REQUIRED_REPORTS:
        report = load_json(report_path)
        require(report.get("verdict") == "GO", f"Report is not GO: {report_path}")
        require(report.get("evidence"), f"Report missing evidence: {report_path}")

    validate_go_hold_issue_reconciliation()

    print("Brain agent-control validation: GO")


if __name__ == "__main__":
    main()
