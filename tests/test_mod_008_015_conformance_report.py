import json
from collections import Counter
from pathlib import Path


REPORT = Path("reports/conformance/MOD-008-015-conformance.json")


def test_mod_008_015_conformance_report_is_internally_consistent() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    requirements = report["requirements"]
    assert report["audited_commit"] == "c18bea9b18551bc656593fd3e0875c3d80695ca0"
    assert report["verdict"] == "HOLD"
    assert len(requirements) == report["counts"]["requirements"] == 117
    counts = Counter(row["overall_status"] for row in requirements)
    assert counts["PASS"] == report["counts"]["PASS"] == 38
    assert counts["PARTIAL"] == report["counts"]["PARTIAL"] == 42
    assert counts["FAIL"] == report["counts"]["FAIL"] == 37
    assert all(row["mandatory"] is True for row in requirements)
    assert len({row["requirement_id"] for row in requirements}) == len(requirements)
    assert {row["module_id"] for row in requirements} == {
        "MOD-008", "MOD-009", "MOD-010", "MOD-011",
        "MOD-012", "MOD-013", "MOD-014", "MOD-015",
    }
    assert all(row["source_refs"] for row in requirements)
    assert all(row["dimensions"] for row in requirements)
    assert all(row["rationale"] for row in requirements)
    assert all(
        row.get("repair_target")
        for row in requirements
        if row["overall_status"] != "PASS"
    )
    assert all(state == "open" for state in report["issue_states"].values())


def test_mod_008_015_module_counts_match_atomic_rows() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    for module_id, expected in report["module_counts"].items():
        actual = Counter(
            row["overall_status"]
            for row in report["requirements"]
            if row["module_id"] == module_id
        )
        assert actual["PASS"] == expected["PASS"]
        assert actual["PARTIAL"] == expected["PARTIAL"]
        assert actual["FAIL"] == expected["FAIL"]
        assert expected["verdict"] == "HOLD"
        assert actual["PARTIAL"] + actual["FAIL"] > 0
