from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .cycle import CognitiveCycle, CognitiveStimulus


@dataclass(slots=True)
class ContinuousCognitionRunner:
    cycle: CognitiveCycle
    inbox: Any
    cycle_runs: Any
    idle_sleep_seconds: float = 1.0
    max_attempts: int = 5

    def run_once(self) -> bool:
        item = self.inbox.claim_next()
        if item is None:
            return False
        try:
            payload = dict(item.get("payload") or {})
            result = self.cycle.process(CognitiveStimulus(
                content=item["content"], source_id=item["source_key"], claim=item["claim"],
                source_reliability=float(payload.get("source_reliability", 0.5)),
                supports=bool(payload.get("supports", True)),
                belief_statement=payload.get("belief_statement"),
                belief_confidence=float(payload.get("belief_confidence", 0.5)),
                commercial_upside=float(payload.get("commercial_upside", 0.0)),
                novelty=float(payload.get("novelty", 0.5)), urgency=float(payload.get("urgency", 0.0)),
                contradiction_value=float(payload.get("contradiction_value", 0.0)),
                uncertainty_reduction=float(payload.get("uncertainty_reduction", 0.5)),
                noise_probability=float(payload.get("noise_probability", 0.2)),
                operator_burden=float(payload.get("operator_burden", 0.0)),
                metadata=payload.get("metadata", {}),
            ))
            self.cycle_runs.save(item["id"], result)
            self.inbox.complete(item["id"])
            return True
        except Exception as exc:  # noqa: BLE001 - job runner must catch any cycle failure to route it to the inbox retry/dead-letter path
            self.inbox.fail(item["id"], repr(exc), retry=int(item.get("attempts", 1)) < self.max_attempts)
            return True

    def run_forever(self) -> None:
        while True:
            if not self.run_once():
                time.sleep(self.idle_sleep_seconds)
