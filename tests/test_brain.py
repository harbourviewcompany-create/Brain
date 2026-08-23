from brain.attention import AttentionMarket, AttentionSignal
from brain.cognitive_state import HomeostaticState, NeuromodulatorState
from brain.domain import Edge, Evidence, Node, Outcome
from brain.homeostasis import HomeostasisEngine
from brain.projections import default_projection_engine
from brain.protocol import EventProtocol
from brain.reward import RewardSystem
from brain.rewiring import RewiringEngine
from brain.runtime import BrainRuntime
from brain.scheduler import CognitiveScheduler, CognitiveTask


def test_belief_updates_and_contradiction_event():
    runtime = BrainRuntime()
    belief = runtime.create_belief("A market is expanding", 0.7)
    evidence = Evidence("Official data shows contraction", "regulator", 0.9)
    updated = runtime.learn(belief, evidence, supports=False)
    assert updated.confidence < belief.confidence
    assert any(e.event_type == "contradiction.detected" for e in runtime.store.events)


def test_rewiring_reinforces_edge():
    a = Node("entity", "a")
    b = Node("entity", "b")
    edge = Edge(a.id, b.id, "related_to", weight=0.5)
    evidence = Evidence("a relates to b", "source", 0.8)
    updated, event = RewiringEngine().reinforce(edge, evidence.id, 0.08)
    assert updated.weight > edge.weight
    assert event.previous["weight"] == 0.5


def test_attention_penalizes_noise():
    market = AttentionMarket()
    clean = AttentionSignal(1, 1, 1, 0.5, 1, 1, 0.1, 0.1)
    noisy = AttentionSignal(1, 1, 1, 0.5, 1, 1, 0.9, 0.9)
    assert market.score(clean) > market.score(noisy)


def test_reward_penalizes_legal_risk():
    system = RewardSystem()
    safe = Outcome(Node("x", "y").id, 1, 0.1, 1, legal_risk=0)
    risky = Outcome(Node("x", "z").id, 1, 0.1, 1, legal_risk=1)
    assert system.score(safe) > system.score(risky)


def test_event_protocol_and_replay():
    runtime = BrainRuntime()
    belief = runtime.create_belief("A signal exists", 0.4)
    evidence = Evidence("Strong support", "official", 1.0)
    runtime.learn(belief, evidence, supports=True)
    protocol = EventProtocol()
    for event in runtime.store.events:
        assert protocol.envelope(event)["protocol_version"] == 1
    state = default_projection_engine().replay(runtime.store.events)
    assert state["event_count"] == len(runtime.store.events)
    assert str(belief.id) or belief.id in state["beliefs"]
    assert state["beliefs"][belief.id]["confidence"] > 0.4


def test_homeostasis_changes_global_modulation():
    engine = HomeostasisEngine()
    modulation = NeuromodulatorState()
    pressured = HomeostaticState(
        compute_load=1,
        unresolved_uncertainty=1,
        memory_pressure=1,
        operator_load=1,
        budget_pressure=1,
        graph_density_pressure=1,
    )
    updated = engine.regulate(pressured, modulation)
    assert updated.stress > 0.5
    assert updated.norepinephrine > 0.5
    assert updated.acetylcholine < 0.7


def test_scheduler_changes_selection_under_stress():
    scheduler = CognitiveScheduler()
    exploratory = CognitiveTask(0.4, 0.1, 1.0, 0.8, 0.3, "explore")
    urgent = CognitiveTask(0.7, 1.0, 0.1, 0.2, 0.2, "urgent")
    calm = NeuromodulatorState(stress=0.0, norepinephrine=0.3, acetylcholine=0.9)
    stressed = NeuromodulatorState(stress=1.0, norepinephrine=1.0, acetylcholine=0.3)
    calm_pick = scheduler.select([exploratory, urgent], calm, 1)[0]
    stressed_pick = scheduler.select([exploratory, urgent], stressed, 1)[0]
    assert stressed_pick.name == "urgent"
    assert calm_pick.name in {"explore", "urgent"}
