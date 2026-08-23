import json
from collections import Counter
from pathlib import Path


CURRENT = Path("reports/conformance/MOD-008-015-conformance.json")
BASELINE = Path("reports/conformance/baseline/MOD-008-015-conformance-c18bea9.json")
GAPS = Path("reports/conformance/MOD-008-015-gap-register.json")


def _effective_rows() -> list[dict]:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    changes = {
        row["requirement_id"]: row["current_status"]
        for row in current["changed_requirements"]
    }
    rows = []
    for row in baseline["requirements"]:
        effective = dict(row)
        effective["overall_status"] = changes.get(
            row["requirement_id"], row["overall_status"]
        )
        rows.append(effective)
    return rows


def test_current_rollforward_reconstructs_complete_117_row_matrix() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    rows = _effective_rows()
    assert current["audited_commit"] == "d8ba4e56dd709af7cb817d7c5d1693dc4b257b05"
    assert current["verdict"] == "HOLD"
    assert len(rows) == current["counts"]["requirements"] == 117
    assert len({row["requirement_id"] for row in rows}) == 117
    counts = Counter(row["overall_status"] for row in rows)
    assert counts == Counter({"PARTIAL": 44, "PASS": 38, "FAIL": 35})
    assert current["counts"]["PASS"] == 38
    assert current["counts"]["PARTIAL"] == 44
    assert current["counts"]["FAIL"] == 35
    assert current["counts"]["NON_PASS"] == 79
    assert all(state == "open" for state in current["issue_states"].values())


def test_rollforward_changes_are_only_evidence_backed_improvements() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    changes = {row["requirement_id"]: row for row in current["changed_requirements"]}
    assert set(changes) == {"M012-FIX", "M013-FIX"}
    for row in changes.values():
        assert row["baseline_status"] == "FAIL"
        assert row["current_status"] == "PARTIAL"
        assert row["evidence"]
        assert row["repair_target"]


def test_current_gap_register_exactly_matches_effective_non_pass_rows() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    gaps = json.loads(GAPS.read_text(encoding="utf-8"))
    rows = _effective_rows()
    expected = {
        row["requirement_id"]
        for row in rows
        if row["overall_status"] != "PASS"
    }
    actual: set[str] = set()
    for module in gaps["gaps"]:
        actual.update(module["partial"])
        actual.update(module["fail"])
    assert gaps["audited_commit"] == current["audited_commit"]
    assert gaps["verdict"] == "HOLD"
    assert len(actual) == gaps["non_pass_count"] == current["counts"]["NON_PASS"] == 79
    assert actual == expected


def test_module_counts_match_effective_rows_and_all_modules_hold() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    rows = _effective_rows()
    for module_id, expected in current["module_counts"].items():
        counts = Counter(
            row["overall_status"] for row in rows if row["module_id"] == module_id
        )
        assert counts["PASS"] == expected["PASS"]
        assert counts["PARTIAL"] == expected["PARTIAL"]
        assert counts["FAIL"] == expected["FAIL"]
        assert expected["verdict"] == "HOLD"
        assert counts["PARTIAL"] + counts["FAIL"] > 0
