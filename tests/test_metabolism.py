from brain.cognitive_state import HomeostaticState, NeuromodulatorState
from brain.cycle import CognitiveCycle, CognitiveStimulus
from brain.domain import utcnow
from brain.homeostasis import HomeostasisEngine
from brain.memory import InMemoryBrainStore
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
    """Wires CapitalLedger into HomeostasisEngine through budget_pressure.

    Capital is now intentionally asymmetric: `budget_pressure` is weighted as
    hunger, not averaged as one inert dashboard dimension. A fully starving
    ledger therefore produces scheduler-relevant stress without requiring
    unrelated uncertainty/operator-load compounding.
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

    assert starving_state.stress_index > 0.6
    assert hungry_modulation.stress > calm_modulation.stress
    assert hungry_modulation.norepinephrine > calm_modulation.norepinephrine
    assert hungry_modulation.acetylcholine < calm_modulation.acetylcholine


def test_deep_multi_pressure_starvation_flips_scheduler_to_the_cheap_certain_payoff():
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


def test_starvation_dominates_action_selection_without_compounding_pressure():
    metabolism = MetabolismEngine()
    homeostasis = HomeostasisEngine()
    scheduler = CognitiveScheduler()

    broke_ledger = CapitalLedger(balance=-50.0, burn_rate=5.0, survival_threshold=0.0, warning_threshold=50.0)
    starvation_state = HomeostaticState(budget_pressure=metabolism.budget_pressure(broke_ledger))
    modulation = homeostasis.regulate(starvation_state, NeuromodulatorState())

    explore_new_source = CognitiveTask(
        utility=0.4, urgency=0.1, novelty=1.0, uncertainty_reduction=0.8, cost=0.3, name="explore_new_source"
    )
    close_known_opportunity = CognitiveTask(
        utility=0.6, urgency=0.9, novelty=0.05, uncertainty_reduction=0.1, cost=0.1, name="close_known_opportunity"
    )

    assert starvation_state.stress_index > 0.6
    assert scheduler.select([explore_new_source, close_known_opportunity], modulation, budget=1)[0].name == (
        "close_known_opportunity"
    )


def test_capital_pressure_reaches_cognitive_cycle_at_runtime():
    store = InMemoryBrainStore()
    ledger = CapitalLedger(balance=1.0, burn_rate=2.0, survival_threshold=0.0, warning_threshold=10.0)
    cycle = CognitiveCycle(store, attention_threshold=-100, capital_ledger=ledger, cognitive_budget=1)

    result = cycle.process(
        CognitiveStimulus(
            content="routine market scan",
            source_id="system",
            claim="market scan available",
            source_reliability=0.8,
            novelty=0.2,
            urgency=0.1,
        )
    )

    kinds = [event.event_type for event in store.events]
    selected_names = [event.payload["name"] for event in store.events if event.event_type == "cognitive_task.selected"]

    assert cycle.capital_ledger is not None
    assert cycle.capital_ledger.is_starving
    assert result.capital_starving is True
    assert result.budget_pressure == 1.0
    assert "capital.metabolized" in kinds
    assert "capital.starvation" in kinds
    assert "homeostasis.budget_pressure_updated" in kinds
    assert selected_names == ["pursue_capital_recovery"]


def test_capital_refresh_merges_budget_pressure_without_zeroing_other_dimensions():
    store = InMemoryBrainStore()
    ledger = CapitalLedger(
        balance=1.0,
        burn_rate=2.0,
        survival_threshold=0.0,
        warning_threshold=10.0,
    )
    cycle = CognitiveCycle(
        store,
        attention_threshold=-100,
        capital_ledger=ledger,
        cognitive_budget=1,
    )
    cycle.homeostatic_state = HomeostaticState(
        compute_load=0.4,
        unresolved_uncertainty=0.55,
        operator_load=0.3,
        graph_density_pressure=0.2,
        budget_pressure=0.0,
    )

    cycle.process(
        CognitiveStimulus(
            content="routine market scan",
            source_id="system",
            claim="market scan available",
            source_reliability=0.8,
            novelty=0.2,
            urgency=0.1,
        )
    )

    state = cycle.homeostatic_state
    assert state.budget_pressure == 1.0
    assert state.compute_load == 0.4
    assert state.unresolved_uncertainty == 0.55
    assert state.operator_load == 0.3
    assert state.graph_density_pressure == 0.2


def test_cycle_outcome_feeds_capital_ledger():
    store = InMemoryBrainStore()
    ledger = CapitalLedger(
        balance=-5.0,
        burn_rate=0.0,
        survival_threshold=0.0,
        warning_threshold=10.0,
        starving_since=utcnow(),
    )
    cycle = CognitiveCycle(store, attention_threshold=-100, capital_ledger=ledger)

    result = cycle.process(
        CognitiveStimulus(
            content="paid outcome posted",
            source_id="operator",
            claim="cash received",
            source_reliability=1.0,
            capital_outcome_amount=20.0,
            capital_outcome_source="operator-confirmed-payment",
        )
    )

    fed_events = [event for event in store.events if event.event_type == "capital.fed"]
    assert cycle.capital_ledger is not None
    assert not cycle.capital_ledger.is_starving
    assert result.capital_starving is False
    assert fed_events
    assert fed_events[0].payload["source"] == "operator-confirmed-payment"
    assert fed_events[0].payload["recovered_from_starvation"] is True
