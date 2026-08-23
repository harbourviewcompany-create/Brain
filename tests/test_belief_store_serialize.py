from uuid import uuid4

from brain.adapters.belief_store import serialize_belief
from brain.domain import Belief, BeliefState
from brain.runtime import BrainRuntime


def test_serialize_belief_shape():
    b = Belief(statement="market expanding", confidence=0.62, state=BeliefState.HYPOTHESIS)
    data = serialize_belief(b)
    assert data["statement"] == "market expanding"
    assert data["confidence"] == 0.62
    assert data["state"] == "hypothesis"
    assert "id" in data


def test_runtime_create_without_projection():
    rt = BrainRuntime()
    b = rt.create_belief("test durable path", 0.55)
    assert b.id in rt.store.beliefs
    assert len(rt.store.events) >= 1


class _FakeProjection:
    def __init__(self):
        self.seen = []

    def upsert(self, belief):
        self.seen.append(belief.id)


class _FakeEvents:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)


def test_runtime_dual_write_hooks():
    proj = _FakeProjection()
    events = _FakeEvents()
    rt = BrainRuntime(event_store=events, belief_projection=proj)
    b = rt.create_belief("dual write", 0.4)
    assert b.id in proj.seen
    assert any(e.event_type == "belief.created" for e in events.events)
