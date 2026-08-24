import json
import re
from pathlib import Path


CURRENT = Path("reports/conformance/MOD-008-015-conformance.json")
GAPS = Path("reports/conformance/MOD-008-015-gap-register.json")
BASELINE = Path("reports/conformance/baseline/MOD-008-015-conformance-c18bea9.json")
REQUIRED_MODULES = {f"MOD-{i:03d}" for i in range(8, 16)}
REQUIRED_REPAIRS = {str(i) for i in range(54, 63)}


def effective_rows() -> list[dict]:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    certifications = current["repair_certifications"]
    result = []
    for row in baseline["requirements"]:
        copied = dict(row)
        status = row["overall_status"]
        if status != "PASS":
            targets = set(re.findall(r"#(\d+)", row.get("repair_target", "")))
            if targets and all(certifications[target]["status"] == "PASS" for target in targets):
                status = "PASS"
        copied["effective_status"] = status
        result.append(copied)
    return result


def test_full_atomic_universe_is_preserved_and_all_117_rows_resolve_to_pass() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    rows = effective_rows()
    assert len(baseline["requirements"]) == 117
    assert len(rows) == 117
    assert len({row["requirement_id"] for row in rows}) == 117
    assert {row["module_id"] for row in rows} == REQUIRED_MODULES
    assert all(row["effective_status"] == "PASS" for row in rows)
    assert current["counts"] == {"requirements": 117, "PASS": 117, "PARTIAL": 0, "FAIL": 0}
    assert current["verdict"] == "GO"


def test_repair_certifications_cover_exactly_54_through_62_with_real_evidence_paths() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    certifications = current["repair_certifications"]
    assert set(certifications) == REQUIRED_REPAIRS
    for certification in certifications.values():
        assert certification["status"] == "PASS"
        assert certification["evidence"]
        for reference in certification["evidence"]:
            path = Path(reference.split(":", 1)[0])
            assert path.exists(), reference


def test_module_counts_are_derived_from_original_requirement_universe() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    rows = effective_rows()
    for module_id in sorted(REQUIRED_MODULES):
        module_rows = [row for row in rows if row["module_id"] == module_id]
        declared = current["module_counts"][module_id]
        assert declared["PASS"] == len(module_rows)
        assert declared["PARTIAL"] == 0
        assert declared["FAIL"] == 0
        assert declared["verdict"] == "GO"


def test_gap_register_is_empty_only_because_effective_original_rows_are_all_pass() -> None:
    gaps = json.loads(GAPS.read_text(encoding="utf-8"))
    assert all(row["effective_status"] == "PASS" for row in effective_rows())
    assert gaps["status"] == "repaired"
    assert gaps["open_gaps"] == []


def test_current_report_cannot_replace_the_atomic_universe_with_summary_requirements() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    assert current["baseline_source"] == str(BASELINE)
    assert current["go_rule"].startswith("All 117 mandatory atomic requirements")
    assert "16-row-summary" in " ".join(current["supersedes"])
    assert "117 atomic requirement IDs" in current["source_preservation"]
