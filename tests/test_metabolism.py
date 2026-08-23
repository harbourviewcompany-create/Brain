from brain.cognitive_state import HomeostaticState, NeuromodulatorState
from brain.domain import utcnow
from brain.homeostasis import HomeostasisEngine
from brain.metabolism import CapitalLedger, MetabolismEngine
from brain.scheduler import CognitiveScheduler, CognitiveTask


def test_metabolize_drains_balance_and_emits_event():
    engine = MetabolismEngine()
    ledger = CapitalLedger(balance=100.0, burn_rate=10.0, survival_threshold=0.0)
    updated, events = engine.metabolize(ledger)
    assert updated.balance == 90.0
    assert not updated.is_starving
    assert events[0].event_type == "capital.metabolized"
    assert len(events) == 1  # no starvation event while still fed


def test_starvation_triggers_when_balance_crosses_survival_threshold():
    engine = MetabolismEngine()
    ledger = CapitalLedger(balance=5.0, burn_rate=10.0, survival_threshold=0.0)
    updated, events = engine.metabolize(ledger)
    assert updated.is_starving
    assert updated.starving_since is not None
    assert any(e.event_type == "capital.starvation" for e in events)


def test_starvation_event_fires_once_not_every_tick():
    engine = MetabolismEngine()
    ledger = CapitalLedger(balance=5.0, burn_rate=10.0, survival_threshold=0.0)
    starved, first_events = engine.metabolize(ledger)
    assert any(e.event_type == "capital.starvation" for e in first_events)
    still_starving, second_events = engine.metabolize(starved)
    assert still_starving.is_starving
    assert not any(e.event_type == "capital.starvation" for e in second_events)
    # onset time is preserved, not reset, across consecutive starving ticks
    assert still_starving.starving_since == starved.starving_since


def test_feeding_recovers_from_starvation():
    engine = MetabolismEngine()
    starving = CapitalLedger(balance=-5.0, burn_rate=10.0, survival_threshold=0.0, starving_since=utcnow())
    fed, event = engine.feed(starving, 50.0, source="opportunity-close")
    assert not fed.is_starving
    assert fed.starving_since is None
    assert event.payload["recovered_from_starvation"] is True


def test_partial_feeding_does_not_clear_starvation():
    engine = MetabolismEngine()
    starving = CapitalLedger(balance=-100.0, burn_rate=10.0, survival_threshold=0.0, starving_since=utcnow())
    fed, event = engine.feed(starving, 10.0, source="small-win")
    assert fed.is_starving
    assert fed.starving_since is not None
    assert event.payload["recovered_from_starvation"] is False


def test_starvation_measurably_raises_stress_and_narrows_exploration():
    """Wires CapitalLedger straight into the existing HomeostasisEngine, with no new
    global state: deficit_ratio IS budget_pressure. Confirms hunger is not inert —
    it moves the same neuromodulator state that already governs the scheduler.

    Note: because HomeostaticState.stress_index is an unweighted mean of six pressure
    dimensions, a fully starving ledger (deficit_ratio=1.0) with every other dimension
    at 0 can only ever contribute ~1/6 of maximum stress under the current formula.
    That's real and worth knowing: as wired today, capital scarcity alone is diluted
    by five unrelated pressures and can't yet dominate action selection the way "money
    is food" implies. This test asserts the real, modest effect — not an idealized one.
    """
    metabolism = MetabolismEngine()
    homeostasis = HomeostasisEngine()

    fed_ledger = CapitalLedger(balance=100.0, burn_rate=1.0, survival_threshold=0.0, warning_threshold=50.0)
    starving_ledger = CapitalLedger(balance=-10.0, burn_rate=1.0, survival_threshold=0.0, warning_threshold=50.0)
    assert not fed_ledger.is_hungry
    assert starving_ledger.is_starving

    fed_state = HomeostaticState(budget_pressure=metabolism.budget_pressure(fed_ledger))
    starving_state = HomeostaticState(budget_pressure=metabolism.budget_pressure(starving_ledger))

    calm_modulation = homeostasis.regulate(fed_state, NeuromodulatorState())
    hungry_modulation = homeostasis.regulate(starving_state, NeuromodulatorState())

    assert hungry_modulation.stress > calm_modulation.stress
    assert hungry_modulation.norepinephrine > calm_modulation.norepinephrine
    assert hungry_modulation.acetylcholine < calm_modulation.acetylcholine


def test_deep_multi_pressure_starvation_flips_scheduler_to_the_cheap_certain_payoff():
    """A single starved dimension isn't enough (see previous test). But hunger rarely
    arrives alone — a brain that is out of money is usually also out of slack: research
    backlog piles up (unresolved_uncertainty), the operator is checking in more
    (operator_load), and the budget itself is the acute pressure. When those move
    together, as they realistically would, the scheduler's own existing math already
    reprioritizes a cheap, certain, known payoff over an expensive novel exploration —
    no new scheduling logic required, just real hunger fed through the pipes that exist.
    """
    metabolism = MetabolismEngine()
    homeostasis = HomeostasisEngine()
    scheduler = CognitiveScheduler()

    broke_ledger = CapitalLedger(balance=-50.0, burn_rate=5.0, survival_threshold=0.0, warning_threshold=50.0)
    assert broke_ledger.is_starving

    compounding_state = HomeostaticState(
        budget_pressure=metabolism.budget_pressure(broke_ledger),
        unresolved_uncertainty=0.6,
        operator_load=0.6,
    )
    modulation = homeostasis.regulate(compounding_state, NeuromodulatorState())

    explore_new_source = CognitiveTask(
        utility=0.4, urgency=0.1, novelty=1.0, uncertainty_reduction=0.8, cost=0.3, name="explore_new_source"
    )
    close_known_opportunity = CognitiveTask(
        utility=0.6, urgency=0.9, novelty=0.05, uncertainty_reduction=0.1, cost=0.1, name="close_known_opportunity"
    )

    calm_pick = scheduler.select([explore_new_source, close_known_opportunity], NeuromodulatorState(), budget=1)[0]
    starved_pick = scheduler.select([explore_new_source, close_known_opportunity], modulation, budget=1)[0]

    assert calm_pick.name == "explore_new_source"
    assert starved_pick.name == "close_known_opportunity"
