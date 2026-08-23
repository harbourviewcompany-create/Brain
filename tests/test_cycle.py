from brain.cycle import CognitiveCycle, CognitiveStimulus
from brain.memory import InMemoryBrainStore
from brain.projections import default_projection_engine
from brain.working_memory import WorkingMemory


class MemoryCheckpointStore:
    def __init__(self):
        self.saved = None

    def save(self, projection_name, *, last_event_id, event_count, state):
        self.saved = {
            "projection_name": projection_name,
            "last_event_id": last_event_id,
            "event_count": event_count,
            "state": state,
        }

    def get(self, projection_name: str):
        if self.saved and self.saved["projection_name"] == projection_name:
            return self.saved
        return None


def test_continuous_cycle_emits_full_cognitive_path():
    store = InMemoryBrainStore()
    checkpoint = MemoryCheckpointStore()
    cycle = CognitiveCycle(store, checkpoint_store=checkpoint, attention_threshold=0.0)
    result = cycle.process(
        CognitiveStimulus(
            content="Regulator published a new licence record",
            source_id="regulator",
            claim="Company A holds licence X",
            source_reliability=0.95,
            commercial_upside=0.8,
            novelty=0.9,
            urgency=0.5,
        )
    )
    kinds = [event.event_type for event in store.events]
    assert kinds == [
        "observation.received",
        "attention.scored",
        "memory.working_stored",
        "belief.created",
        "evidence.created",
        "belief.updated",
        "cognitive_task.selected",
        "cycle.completed",
    ]
    assert result.task_ids
    assert result.working_memory_size == 1
    assert checkpoint.saved["event_count"] == len(store.events)


def test_contradiction_creates_investigation_task():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store, attention_threshold=-100)
    first = cycle.process(
        CognitiveStimulus(
            content="Source says licence active",
            source_id="source-a",
            claim="Licence is active",
            source_reliability=0.9,
            supports=True,
            belief_statement="Licence is active",
        )
    )
    second = cycle.process(
        CognitiveStimulus(
            content="Regulator says licence revoked",
            source_id="regulator",
            claim="Licence was revoked",
            source_reliability=1.0,
            supports=False,
            belief_id=first.belief_id,
            contradiction_value=1.0,
        )
    )
    assert second.contradiction_detected is True
    selected = [e for e in store.events if e.event_type == "cognitive_task.selected"]
    assert any(e.payload["name"] == "investigate_contradiction" for e in selected)


def test_replay_recovers_belief_state_after_cycle():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store)
    result = cycle.process(
        CognitiveStimulus(
            content="Evidence",
            source_id="s",
            claim="A is B",
            source_reliability=0.8,
        )
    )
    state = default_projection_engine().replay(store.events)
    assert result.belief_id in state["beliefs"]
    assert state["beliefs"][result.belief_id]["statement"] == "A is B"


def test_working_memory_eviction_emits_events_under_capacity_pressure():
    store = InMemoryBrainStore()
    wm = WorkingMemory(capacity=1)
    cycle = CognitiveCycle(store, working_memory=wm, attention_threshold=-100)
    cycle.process(
        CognitiveStimulus(
            content="first",
            source_id="s",
            claim="c1",
            source_reliability=0.5,
            novelty=0.1,
        )
    )
    cycle.process(
        CognitiveStimulus(
            content="second",
            source_id="s",
            claim="c2",
            source_reliability=0.9,
            novelty=0.9,
        )
    )
    kinds = [e.event_type for e in store.events]
    assert kinds.count("memory.working_stored") == 2
    assert "memory.working_evicted" in kinds
    assert cycle.working_memory.size == 1


def test_second_cycle_uses_incremental_checkpoint():
    store = InMemoryBrainStore()
    checkpoint = MemoryCheckpointStore()
    cycle = CognitiveCycle(store, checkpoint_store=checkpoint, attention_threshold=-100)
    cycle.process(
        CognitiveStimulus(content="one", source_id="s", claim="A", source_reliability=0.8)
    )
    first_count = checkpoint.saved["event_count"]
    cycle.process(
        CognitiveStimulus(content="two", source_id="s", claim="B", source_reliability=0.8)
    )
    assert checkpoint.saved["event_count"] > first_count
    assert checkpoint.saved["event_count"] == len(store.events)
