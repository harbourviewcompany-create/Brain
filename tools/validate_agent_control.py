#!/usr/bin/env python3
"""Validate Brain agent-control files.

This is a documentation/control gate. It does not prove the Brain is built.
It prevents agents from claiming readiness while required control artifacts,
fixtures, traceability rows, or GO/HOLD fields are missing.
"""
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
]

REQUIRED_FIXTURES = [
    "tests/fixtures/brain/source_signal_evidence_belief.json",
    "tests/fixtures/brain/formula_run_attention_reward.json",
    "tests/fixtures/brain/approval_gate_external_action.json",
    "tests/fixtures/brain/outcome_reward_pain_learning.json",
    "tests/fixtures/brain/contradiction_review.json",
    "tests/fixtures/brain/acceptance_gate_go_hold.json",
]


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as f:
        return json.load(f)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    missing = [p for p in REQUIRED_FILES + REQUIRED_FIXTURES if not (ROOT / p).exists()]
    require(not missing, f"Missing required Brain agent-control artifacts: {missing}")

    task_queue = load_json("docs/agent-control/task-queue.json")
    tasks = task_queue.get("tickets", [])
    require(tasks, "task-queue.json must contain tickets")
    for task in tasks:
        for field in ["ticket_id", "objective", "files_to_create_or_modify", "required_tests", "required_fixtures", "acceptance_criteria", "go_hold_condition"]:
            require(field in task, f"Task missing {field}: {task}")

    acceptance = load_json("docs/spec/acceptance-matrix.json")
    rules = acceptance.get("rules", [])
    require(rules, "acceptance-matrix.json must contain rules")
    for rule in rules:
        require(rule.get("go_hold_status") in {"GO", "HOLD"}, f"Acceptance rule missing GO/HOLD: {rule}")
        require(rule.get("required_evidence"), f"Acceptance rule missing evidence: {rule}")

    traceability = load_json("docs/spec/source-to-build-traceability.json")
    rows = traceability.get("traceability", [])
    require(rows, "source-to-build traceability must contain rows")
    required_row_fields = ["concept_family", "source_section", "module", "schema", "service", "formula", "test", "fixture", "dashboard", "acceptance_rule"]
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

    referenced_fixtures = set()
    for task in tasks:
        referenced_fixtures.update(task.get("required_fixtures", []))
    referenced_fixtures.discard("all_required_fixture_files")
    referenced_fixtures.discard("none")
    missing_referenced = sorted(referenced_fixtures - fixture_ids)
    require(not missing_referenced, f"Referenced fixtures are not materialized: {missing_referenced}")

    print("Brain agent-control validation: GO")


if __name__ == "__main__":
    main()
