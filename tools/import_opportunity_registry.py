#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tools.revenue_spine_17_21 import (
    FAST_CASH_COUNT,
    REGISTRY_TARGET_COUNT,
    first_500_fast_cash,
    generate_opportunity_registry,
    registry_summary,
)


def build_import_payload(count: int = REGISTRY_TARGET_COUNT) -> dict[str, object]:
    rows = generate_opportunity_registry(count)
    fast_cash = first_500_fast_cash(rows)
    return {
        "registry": [asdict(row) for row in rows],
        "first_500_fast_cash": [asdict(row) for row in fast_cash],
        "summary": registry_summary(rows),
    }


def write_payload(output_dir: Path, payload: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "generated_10000_opportunity_registry.json").write_text(
        json.dumps(payload["registry"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "generated_first_500_fast_cash.json").write_text(
        json.dumps(payload["first_500_fast_cash"], indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and materialize the Money Spine opportunity registry.")
    parser.add_argument("--count", type=int, default=REGISTRY_TARGET_COUNT)
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--output-dir", default="data/opportunities/generated")
    args = parser.parse_args()
    payload = build_import_payload(args.count)
    if args.write_json:
        write_payload(Path(args.output_dir), payload)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    assert len(payload["first_500_fast_cash"]) == min(args.count, FAST_CASH_COUNT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
