from brain.cycle import CognitiveCycle, CognitiveStimulus
from brain.memory import InMemoryBrainStore
from brain.projections import default_projection_engine


class MemoryCheckpointStore:
    def __init__(self): self.saved = None
    def save(self, projection_name, *, last_event_id, event_count, state):
        self.saved = {"projection_name": projection_name, "last_event_id": last_event_id, "event_count": event_count, "state": state}


def test_continuous_cycle_emits_full_cognitive_path():
    store = InMemoryBrainStore(); checkpoint = MemoryCheckpointStore()
    cycle = CognitiveCycle(store, checkpoint_store=checkpoint, attention_threshold=0.0)
    result = cycle.process(CognitiveStimulus(content="Regulator published a new licence record", source_id="regulator", claim="Company A holds licence X", source_reliability=0.95, commercial_upside=0.8, novelty=0.9, urgency=0.5))
    kinds = [event.event_type for event in store.events]
    assert kinds == ["observation.received","attention.scored","memory.working_stored","belief.created","evidence.created","belief.updated","cognitive_task.selected","cycle.completed"]
    assert result.task_ids
    assert checkpoint.saved["event_count"] == len(store.events)


def test_contradiction_creates_investigation_task():
    store = InMemoryBrainStore(); cycle = CognitiveCycle(store, attention_threshold=-100)
    first = cycle.process(CognitiveStimulus(content="Source says licence active", source_id="source-a", claim="Licence is active", source_reliability=0.9, supports=True, belief_statement="Licence is active"))
    second = cycle.process(CognitiveStimulus(content="Regulator says licence revoked", source_id="regulator", claim="Licence was revoked", source_reliability=1.0, supports=False, belief_id=first.belief_id, contradiction_value=1.0))
    assert second.contradiction_detected is True
    selected = [e for e in store.events if e.event_type == "cognitive_task.selected"]
    assert any(e.payload["name"] == "investigate_contradiction" for e in selected)


def test_replay_recovers_belief_state_after_cycle():
    store = InMemoryBrainStore(); cycle = CognitiveCycle(store)
    result = cycle.process(CognitiveStimulus(content="Evidence", source_id="s", claim="A is B", source_reliability=0.8))
    state = default_projection_engine().replay(store.events)
    assert result.belief_id in state["beliefs"]
    assert state["beliefs"][result.belief_id]["statement"] == "A is B"
