from __future__ import annotations

from typing import Any
from uuid import UUID

from .domain import Belief, BeliefState
from .projections import default_projection_engine


def hydrate_belief_cache(
    belief_cache: dict[UUID, Belief],
    event_store: Any,
    checkpoint_store: Any | None = None,
    *,
    from_checkpoint: bool = True,
) -> int:
    """Load beliefs into belief_cache from checkpoint or full event replay."""
    state: dict[str, Any] | None = None
    if from_checkpoint and checkpoint_store is not None and hasattr(checkpoint_store, "get"):
        prior = checkpoint_store.get("brain.current")
        if prior and prior.get("state"):
            state = dict(prior["state"])

    if state is None:
        events = event_store.read_all() if hasattr(event_store, "read_all") else []
        state = default_projection_engine().replay(list(events))

    beliefs = state.get("beliefs") or {}
    loaded = 0
    for key, payload in beliefs.items():
        try:
            bid = key if isinstance(key, UUID) else UUID(str(key))
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        statement = str(payload.get("statement") or "")
        confidence = float(payload.get("confidence", 0.5))
        raw_state = payload.get("state", "hypothesis")
        try:
            bstate = BeliefState(str(raw_state).split(".")[-1].lower()) if raw_state else BeliefState.HYPOTHESIS
        except ValueError:
            bstate = BeliefState.HYPOTHESIS
        version = int(payload.get("version", 1))
        belief_cache[bid] = Belief(
            statement=statement, confidence=confidence, state=bstate, id=bid, version=version
        )
        loaded += 1
    return loaded
