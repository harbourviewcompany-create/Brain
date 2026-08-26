from uuid import uuid4

from brain.cycle import CognitiveCycle
from brain.memory import InMemoryBrainStore
from brain.runner import ContinuousCognitionRunner


class Inbox:
    def __init__(self, item):
        self.item = item
        self.completed = []
        self.failed = []

    def claim_next(self):
        item, self.item = self.item, None
        return item

    def complete(self, item_id):
        self.completed.append(item_id)

    def fail(self, item_id, error, retry=True):
        self.failed.append((item_id, error, retry))


class Runs:
    def __init__(self):
        self.saved = []

    def save(self, inbox_id, result):
        self.saved.append((inbox_id, result))


def test_runner_claims_processes_and_completes_stimulus():
    item_id = uuid4()
    inbox = Inbox(
        {
            "id": item_id,
            "source_key": "regulator",
            "content": "New licence",
            "claim": "Company A licensed",
            "payload": {"source_reliability": 0.95, "novelty": 0.8},
            "attempts": 1,
        }
    )
    runs = Runs()
    runner = ContinuousCognitionRunner(CognitiveCycle(InMemoryBrainStore()), inbox, runs)

    assert runner.run_once() is True
    assert inbox.completed == [item_id]
    assert len(runs.saved) == 1
    assert inbox.failed == []


def test_runner_returns_false_when_idle():
    # Endogenous mind is opt-in for this unit: empty inbox must report idle.
    runner = ContinuousCognitionRunner(
        CognitiveCycle(InMemoryBrainStore()),
        Inbox(None),
        Runs(),
        enable_endogenous=False,
    )
    assert runner.run_once() is False
