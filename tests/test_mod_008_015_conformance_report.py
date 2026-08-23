import json
from pathlib import Path


CURRENT = Path("reports/conformance/MOD-008-015-conformance.json")
GAPS = Path("reports/conformance/MOD-008-015-gap-register.json")
REQUIRED_MODULES = {f"MOD-{i:03d}" for i in range(8, 16)}
REQUIRED_REPAIRS = {str(i) for i in range(54, 63)}


def test_repaired_conformance_report_marks_all_modules_go() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    assert current["verdict"] == "GO"
    assert current["audit_status"] == "atomic_repair_implemented"
    assert REQUIRED_MODULES == set(current["modules"])
    for module_id, module in current["modules"].items():
        assert module_id in REQUIRED_MODULES
        assert module["verdict"] == "GO"
        assert module["requirements"]
        for row in module["requirements"]:
            assert row["mandatory"] is True
            assert row["status"] == "PASS"
            assert row["evidence"]


def test_repair_issues_are_all_mapped_to_pass() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    assert set(current["repair_issues"]) == REQUIRED_REPAIRS
    assert all(status == "PASS" for status in current["repair_issues"].values())
    assert current["supersedes"]


def test_gap_register_is_cleared_after_repair() -> None:
    gaps = json.loads(GAPS.read_text(encoding="utf-8"))
    assert gaps["status"] == "repaired"
    assert gaps["open_gaps"] == []
    assert len(gaps["closed_gaps"]) >= len(REQUIRED_REPAIRS)
    closed_issue_ids = {
        str(issue)
        for gap in gaps["closed_gaps"]
        for issue in gap.get("issues", [])
    }
    assert REQUIRED_REPAIRS <= closed_issue_ids
    assert gaps["go_hold"].startswith("GO")


def test_historical_hold_state_is_preserved_by_supersession_not_deletion() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    superseded = " ".join(current["supersedes"])
    assert "MOD-008-015-economic-runtime.json" in superseded
    assert "MOD-008-015-conformance.md@HOLD" in superseded
    assert "MOD-008-015-gap-register.json@open" in superseded
