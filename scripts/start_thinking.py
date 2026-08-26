#!/usr/bin/env python3
"""Start the Brain thinking on its own (endogenous mind loop).

Usage:
  python scripts/start_thinking.py
  python scripts/start_thinking.py --ticks 20
  python scripts/start_thinking.py --forever
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.heartbeat import build_default_heartbeat  # noqa: E402
from brain.endogenous import ENDOGENOUS_SOURCE_KEY  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run autonomous endogenous cognition")
    parser.add_argument("--ticks", type=int, default=12, help="Number of cognitive cycles")
    parser.add_argument("--forever", action="store_true", help="Run until interrupted")
    parser.add_argument("--sleep", type=float, default=0.02, help="Pause between ticks")
    args = parser.parse_args()

    hb = build_default_heartbeat()
    seeded = hb.bootstrap_mind()
    print(f"[bootstrap] seeded {seeded} foundational beliefs")
    for b in list(hb._cycle._belief_cache.values())[:6]:
        print(f"  • ({b.confidence:.2f}) {b.statement}")
        for u in (b.unknowns or [])[:2]:
            print(f"      ? {u}")

    if args.forever:
        print("\n[run_forever] Ctrl+C to stop\n")
        try:
            n = 0
            while True:
                snap = hb.tick(max_items=1)
                n += 1
                _print_cycle(n, snap, hb)
                if snap.get("processed_this_call", 0) == 0:
                    time.sleep(hb.idle_sleep_seconds)
        except KeyboardInterrupt:
            print("\n[stop]")
            _print_status(hb)
            return 0

    print(f"\n[thinking] {args.ticks} cycles (curiosity + dreams + self-model + GWT)...\n")
    for i in range(args.ticks):
        snap = hb.tick(max_items=1)
        _print_cycle(i + 1, snap, hb)
        time.sleep(max(0.0, args.sleep))

    _print_status(hb)
    events = hb.event_store.read_all() if hasattr(hb.event_store, "read_all") else []
    endogenous_obs = [
        e for e in events
        if getattr(e, "event_type", None) == "observation.received"
        and (getattr(e, "payload", {}) or {}).get("source_id") == ENDOGENOUS_SOURCE_KEY
    ]
    night = [e for e in events if getattr(e, "event_type", None) == "dream.night_phase"]
    print(f"[events] total={len(events)} endogenous_obs={len(endogenous_obs)} night_phase={len(night)}")
    print("[done]")
    return 0


def _print_cycle(n: int, snap: dict, hb) -> None:
    cycles = snap.get("cycles") or []
    phase = str(hb._cycle.circadian.phase)
    if not cycles:
        print(f"  tick {n}: idle phase={phase}")
        return
    c = cycles[-1]
    mind = hb.mind.status()
    focus = (mind.get("last_focus") or "")[:50]
    print(
        f"  tick {n}: att={c.get('attention_score', 0):.2f} "
        f"wm={c.get('working_memory_size')} "
        f"phase={phase} "
        f"curiosity_open={mind.get('open_curiosity')} "
        f"self={mind.get('self_model_phase')} "
        f"focus={focus!r}"
    )


def _print_status(hb) -> None:
    st = hb.status()
    mind = st.get("mind") or {}
    print("\n[status]")
    print(f"  ticks={st.get('ticks')} processed={st.get('total_processed')} beliefs={st.get('belief_cache_size')}")
    print(f"  circadian={st.get('circadian_phase')} pressure={st.get('sleep_pressure'):.3f} awake={st.get('is_awake')}")
    print(f"  curiosity open={mind.get('open_curiosity')} resolved={mind.get('curiosity_resolved')}")
    print(f"  self_model={mind.get('self_model_phase')} stress={mind.get('stress_index')}")
    print(f"  night_runs={mind.get('night_phase_runs')} last_focus={mind.get('last_focus')!r}")
    ws = mind.get("workspace") or {}
    print(f"  workspace items={ws.get('workspace_items')} active={ws.get('active_focus')}")


if __name__ == "__main__":
    raise SystemExit(main())
