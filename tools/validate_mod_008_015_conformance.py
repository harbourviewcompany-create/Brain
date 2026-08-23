from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "conformance" / "MOD-008-015-conformance.json"
GAPS = ROOT / "reports" / "conformance" / "MOD-008-015-gap-register.json"
BASELINE = ROOT / "reports" / "conformance" / "baseline" / "MOD-008-015-conformance-c18bea9.json"
REQUIRED_MODULES = {f"MOD-{i:03d}" for i in range(8, 16)}
REQUIRED_REPAIRS = {str(i) for i in range(54, 63)}
STATUS_VALUES = {"PASS", "PARTIAL", "FAIL"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def repair_ids(row: dict) -> set[str]:
    target = str(row.get("repair_target", ""))
    return set(re.findall(r"#(\d+)", target))


def evidence_paths_exist(evidence: list[str]) -> bool:
    for reference in evidence:
        path = reference.split(":", 1)[0]
        if not path or not (ROOT / path).exists():
            return False
    return True


def main() -> None:
    baseline = load_json(BASELINE)
    report = load_json(REPORT)
    gaps = load_json(GAPS)
    errors: list[str] = []

    rows = baseline.get("requirements", [])
    if len(rows) != 117:
        errors.append(f"baseline atomic universe must contain 117 rows, found {len(rows)}")
    row_ids = [str(row.get("requirement_id")) for row in rows]
    if len(set(row_ids)) != len(row_ids):
        errors.append("baseline requirement IDs must be unique")
    if set(row.get("module_id") for row in rows) != REQUIRED_MODULES:
        errors.append("baseline must cover exactly MOD-008 through MOD-015")

    baseline_ref = report.get("baseline_source")
    expected_ref = "reports/conformance/baseline/MOD-008-015-conformance-c18bea9.json"
    if baseline_ref != expected_ref:
        errors.append("current report must preserve the immutable 117-row baseline_source")
    if not report.get("audited_commit"):
        errors.append("current report requires audited_commit")
    if report.get("go_rule") != "All 117 mandatory atomic requirements must PASS on one evidence-bearing implementation commit.":
        errors.append("current report must preserve the 117-row GO rule")

    certifications = report.get("repair_certifications", {})
    if set(certifications) != REQUIRED_REPAIRS:
        errors.append("repair certifications must cover exactly issues #54 through #62")
    for issue_id, certification in certifications.items():
        if certification.get("status") not in {"PASS", "HOLD"}:
            errors.append(f"repair certification #{issue_id} has invalid status")
        evidence = certification.get("evidence", [])
        if not evidence:
            errors.append(f"repair certification #{issue_id} missing evidence")
        elif not evidence_paths_exist(evidence):
            errors.append(f"repair certification #{issue_id} references missing evidence")

    effective: list[tuple[dict, str]] = []
    for row in rows:
        status = str(row.get("overall_status"))
        if status not in STATUS_VALUES:
            errors.append(f"{row.get('requirement_id')} invalid baseline status {status}")
            continue
        if status != "PASS":
            targets = repair_ids(row)
            if not targets:
                errors.append(f"{row.get('requirement_id')} non-PASS baseline row has no repair target")
            elif not targets <= REQUIRED_REPAIRS:
                errors.append(f"{row.get('requirement_id')} has unknown repair target(s) {sorted(targets)}")
            elif all(certifications.get(target, {}).get("status") == "PASS" for target in targets):
                status = "PASS"
        effective.append((row, status))

    counts = {
        "requirements": len(effective),
        "PASS": sum(status == "PASS" for _, status in effective),
        "PARTIAL": sum(status == "PARTIAL" for _, status in effective),
        "FAIL": sum(status == "FAIL" for _, status in effective),
    }
    if report.get("counts") != counts:
        errors.append(f"declared counts {report.get('counts')} do not equal effective counts {counts}")

    module_counts: dict[str, dict[str, int | str]] = {}
    for module_id in sorted(REQUIRED_MODULES):
        module_rows = [(row, status) for row, status in effective if row.get("module_id") == module_id]
        nonpass = [status for _, status in module_rows if status != "PASS"]
        module_counts[module_id] = {
            "PASS": sum(status == "PASS" for _, status in module_rows),
            "PARTIAL": sum(status == "PARTIAL" for _, status in module_rows),
            "FAIL": sum(status == "FAIL" for _, status in module_rows),
            "verdict": "HOLD" if nonpass else "GO",
        }
    if report.get("module_counts") != module_counts:
        errors.append("declared module_counts do not equal effective 117-row module counts")

    expected_verdict = "GO" if counts["PASS"] == 117 else "HOLD"
    if report.get("verdict") != expected_verdict:
        errors.append(f"verdict must be {expected_verdict} for effective atomic counts")

    open_gap_ids = {str(item.get("requirement_id")) for item in gaps.get("open_gaps", []) if isinstance(item, dict)}
    expected_open = {str(row.get("requirement_id")) for row, status in effective if status != "PASS"}
    if open_gap_ids != expected_open:
        errors.append("gap register must equal the complete effective non-PASS atomic requirement set")
    if gaps.get("status") != ("repaired" if not expected_open else "open"):
        errors.append("gap-register status does not match effective atomic state")

    if expected_verdict == "GO" and any(certifications[str(i)].get("status") != "PASS" for i in range(54, 63)):
        errors.append("GO requires every repair certification #54-#62 to PASS")

    if errors:
        raise SystemExit("\n".join(errors))

    print(
        "MOD-008-015 atomic conformance validator: "
        f"{expected_verdict} ({counts['PASS']}/117 PASS; {counts['PARTIAL']} PARTIAL; {counts['FAIL']} FAIL)"
    )


if __name__ == "__main__":
    main()
