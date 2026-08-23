from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "conformance" / "MOD-008-015-conformance.json"
GAPS = ROOT / "reports" / "conformance" / "MOD-008-015-gap-register.json"
REQUIRED_MODULES = {f"MOD-{i:03d}" for i in range(8, 16)}
REQUIRED_EVIDENCE = [
    "brain/economic_conformance.py",
    "tests/test_mod_008_015_conformance_repairs.py",
    "tests/fixtures/brain/mod_008_015_complete_fixture_universe.json",
    "docs/operator-surfaces/mod-008-015-complete-operator-surfaces.json",
    "reports/acceptance/MOD-008-015-atomic-repair.json",
    "reports/go-hold/MOD-008-015-GO-HOLD.json",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    report = load_json(REPORT)
    gaps = load_json(GAPS)
    errors: list[str] = []

    if report.get("verdict") != "GO":
        errors.append("MOD-008-015 conformance verdict must be GO")

    modules = report.get("modules", {})
    missing_modules = REQUIRED_MODULES - set(modules)
    if missing_modules:
        errors.append(f"missing module reports: {sorted(missing_modules)}")

    for module_id in sorted(REQUIRED_MODULES):
        module = modules.get(module_id, {})
        if module.get("verdict") != "GO":
            errors.append(f"{module_id} verdict is not GO")
        for requirement in module.get("requirements", []):
            if requirement.get("mandatory") is True and requirement.get("status") != "PASS":
                errors.append(f"{module_id}:{requirement.get('requirement_id')} is non-PASS")
            evidence = requirement.get("evidence", [])
            if requirement.get("mandatory") is True and not evidence:
                errors.append(f"{module_id}:{requirement.get('requirement_id')} missing evidence")

    if gaps.get("open_gaps") not in ([], 0):
        errors.append("gap register still has open gaps")

    for path in REQUIRED_EVIDENCE:
        if not (ROOT / path).exists():
            errors.append(f"missing evidence path: {path}")

    if not report.get("supersedes"):
        errors.append("conformance report must supersede prior aggregate GO/HOLD contradictions")

    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
