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
        "perception.encoded",
        "attention.scored",
        "memory.working_stored",
        "belief.created",
        "evidence.created",
        "theory_of_mind.belief_attributed",
        "belief.updated",
        "hedonic.outcome_registered",
        "affect.appraised",
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


def test_contradiction_triggers_executive_arbitration_between_competing_tasks():
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
    # Two competing tasks (consolidate + investigate) means the executive
    # layer should have actually run and reported a decision, not just
    # left the field empty.
    assert second.executive_override_attempted is not None
    arbitrated = [e for e in store.events if e.event_type == "executive.arbitrated"]
    assert len(arbitrated) == 1
    assert arbitrated[0].payload["chosen"] in ("investigate_contradiction", "consolidate_observation")


def test_cycle_result_reports_affect_and_perception_and_circadian_state():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store, attention_threshold=-100)
    result = cycle.process(
        CognitiveStimulus(
            content="we saw strong growth and a big win this quarter",
            source_id="analyst",
            claim="Revenue grew",
            source_reliability=0.9,
            supports=True,
        )
    )
    assert result.emotion_label is not None
    assert result.emotion_valence is not None
    assert result.circadian_phase == "wake"
    assert result.perceived_novelty == 1.0  # first time this content is seen

    appraised = [e for e in store.events if e.event_type == "affect.appraised"]
    assert len(appraised) == 1


def test_theory_of_mind_tracks_source_claims_across_cycles():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store, attention_threshold=-100)
    result = cycle.process(
        CognitiveStimulus(
            content="Regulator confirms licence renewal",
            source_id="regulator",
            claim="Licence renewed",
            source_reliability=0.95,
            supports=True,
        )
    )
    assert result.agent_trust is not None
    agent_model = cycle.theory_of_mind.agents["regulator"]
    assert "Licence renewed" in agent_model.attributed_beliefs


def test_contradiction_emits_hedonic_pain_event():
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
    cycle.process(
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
    pain_events = [e for e in store.events if e.event_type == "hedonic.pain_registered"]
    assert len(pain_events) == 1
    assert pain_events[0].payload["intensity"] > 0


def test_theory_of_mind_attribution_emits_event_every_cycle():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store, attention_threshold=-100)
    cycle.process(
        CognitiveStimulus(
            content="Regulator confirms licence renewal",
            source_id="regulator",
            claim="Licence renewed",
            source_reliability=0.95,
            supports=True,
        )
    )
    attributed = [e for e in store.events if e.event_type == "theory_of_mind.belief_attributed"]
    assert len(attributed) == 1
    assert attributed[0].payload["agent_id"] == "regulator"
    assert attributed[0].payload["statement"] == "Licence renewed"


def test_circadian_phase_change_emits_event():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store, attention_threshold=-100)
    cycle.circadian.pressure.level = 0.9
    cycle.circadian.oscillator.phase_position = 0.0
    cycle.circadian.sleep_onset_pressure = 0.5

    cycle.process(
        CognitiveStimulus(
            content="routine update",
            source_id="system",
            claim="all clear",
            urgency=0.1,
        )
    )
    phase_events = [e for e in store.events if e.event_type == "circadian.phase_changed"]
    assert len(phase_events) == 1
    assert phase_events[0].payload["previous_phase"] == "wake"
    assert phase_events[0].payload["new_phase"] == "nrem"


def test_circadian_forced_wake_emits_event():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store, attention_threshold=-100)
    cycle.circadian.pressure.level = 0.9
    cycle.circadian.oscillator.phase_position = 0.0
    cycle.circadian.sleep_onset_pressure = 0.5
    cycle.circadian.advance(ticks=0.1)
    assert not cycle.circadian.is_awake

    cycle.process(
        CognitiveStimulus(
            content="critical breach detected right now",
            source_id="system",
            claim="breach in progress",
            urgency=0.95,
        )
    )
    forced_wake_events = [e for e in store.events if e.event_type == "circadian.forced_wake"]
    assert len(forced_wake_events) == 1
    assert forced_wake_events[0].payload["previous_phase"] == "nrem"


def test_forced_sleep_reduces_encoding_via_low_control_and_urgency_can_wake_it():
    store = InMemoryBrainStore()
    cycle = CognitiveCycle(store, attention_threshold=-100)
    cycle.circadian.pressure.level = 0.9
    cycle.circadian.oscillator.phase_position = 0.0
    cycle.circadian.sleep_onset_pressure = 0.5
    cycle.circadian.advance(ticks=0.1)
    assert not cycle.circadian.is_awake

    # A routine, non-urgent stimulus should not force a wake.
    cycle.process(
        CognitiveStimulus(
            content="routine housekeeping ping",
            source_id="system",
            claim="heartbeat ok",
            urgency=0.1,
        )
    )
    assert not cycle.circadian.is_awake

    # A highly urgent stimulus should force-wake the Brain rather than
    # being silently processed at near-zero encoding rate.
    cycle.process(
        CognitiveStimulus(
            content="critical breach detected right now",
            source_id="system",
            claim="breach in progress",
            urgency=0.95,
        )
    )
    assert cycle.circadian.is_awake


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
