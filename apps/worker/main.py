from __future__ import annotations

import os

from brain.adapters.cognition import CognitiveCycleRunStore, PostgresSensoryInbox
from brain.adapters.postgres import PostgresEventStore, ProjectionCheckpointStore
from brain.cycle import CognitiveCycle
from brain.runner import ContinuousCognitionRunner


def build_runner() -> ContinuousCognitionRunner:
    dsn = os.environ["DATABASE_URL"]
    event_store = PostgresEventStore(dsn)
    checkpoint_store = ProjectionCheckpointStore(event_store.pool)
    cycle = CognitiveCycle(event_store, checkpoint_store=checkpoint_store)
    inbox = PostgresSensoryInbox(event_store.pool)
    runs = CognitiveCycleRunStore(event_store.pool)
    return ContinuousCognitionRunner(cycle, inbox, runs)


def main() -> None:
    build_runner().run_forever()


if __name__ == "__main__":
    main()
