from uuid import uuid4

from brain.attribution import OutcomeAttribution
from brain.domain import Edge, Node, Outcome
from brain.dreaming import ReplayConsolidationEngine


def _edge(source, target, relation, weight=0.5, confidence=0.5):
    return Edge(source, target, relation, weight=weight, confidence=confidence)


def test_consolidate_with_no_outcomes_is_a_true_noop():
    attribution = OutcomeAttribution()
    engine = ReplayConsolidationEngine(attribution)
    result = engine.consolidate([], edges_by_outcome={})
    assert result.updated_edges == []
    assert result.replayed_outcome_ids == []


def test_consolidate_replays_real_outcomes_and_updates_weights():
    a, b = Node("e", "source"), Node("e", "claim")
    edge = _edge(a.id, b.id, "supports", weight=0.5)
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0, edge_ids=[edge.id])

    attribution = OutcomeAttribution(edge_learn_rate=0.08)
    engine = ReplayConsolidationEngine(attribution, replay_rate_scale=0.4)
    result = engine.consolidate([outcome], edges_by_outcome={outcome.action_id: [edge]})

    assert outcome.id in result.replayed_outcome_ids
    assert result.updated_edges
    assert result.updated_edges[0].weight > 0.5


def test_consolidation_uses_a_reduced_rate_and_restores_it_afterward():
    a, b = Node("e", "source"), Node("e", "claim")
    edge = _edge(a.id, b.id, "supports", weight=0.5)
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0, edge_ids=[edge.id])

    attribution = OutcomeAttribution(edge_learn_rate=0.08)
    engine = ReplayConsolidationEngine(attribution, replay_rate_scale=0.4)
    result = engine.consolidate([outcome], edges_by_outcome={outcome.action_id: [edge]})

    assert result.consolidation_learn_rate == 0.08 * 0.4
    # base rate is restored once consolidation finishes -- it must not
    # leak into ordinary waking attribution afterward
    assert attribution.base_edge_learn_rate == 0.08


def test_consolidation_replay_produces_a_smaller_delta_than_a_waking_update_would():
    a, b = Node("e", "source"), Node("e", "claim")
    awake_edge = _edge(a.id, b.id, "supports", weight=0.5)
    asleep_edge = _edge(a.id, b.id, "supports", weight=0.5)
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0, edge_ids=[awake_edge.id])

    awake = OutcomeAttribution(edge_learn_rate=0.08)
    awake_result = awake.attribute(outcome, edges=[awake_edge])
    awake_delta = awake_result.attribution.edge_deltas[str(awake_edge.id)]

    asleep_attribution = OutcomeAttribution(edge_learn_rate=0.08)
    engine = ReplayConsolidationEngine(asleep_attribution, replay_rate_scale=0.4)
    consolidation_result = engine.consolidate([outcome], edges_by_outcome={outcome.action_id: [asleep_edge]})
    asleep_delta = consolidation_result.updated_edges[0].weight - 0.5

    assert asleep_delta < awake_delta


def test_consolidate_prioritizes_most_salient_outcomes_when_over_the_cap():
    a, b = Node("e", "source"), Node("e", "claim")
    outcomes = []
    edges_by_outcome = {}
    for i in range(5):
        edge = _edge(a.id, b.id, "supports", weight=0.5)
        outcome = Outcome(
            action_id=uuid4(),
            value_created=0.01 * i,  # rising salience: 0.0, 0.01, 0.02, 0.03, 0.04
            operator_time_cost=0.05,
            prediction_accuracy=0.5,
            edge_ids=[edge.id],
        )
        outcomes.append(outcome)
        edges_by_outcome[outcome.action_id] = [edge]

    attribution = OutcomeAttribution()
    engine = ReplayConsolidationEngine(attribution, max_replays=2)
    result = engine.consolidate(outcomes, edges_by_outcome=edges_by_outcome)

    assert len(result.replayed_outcome_ids) == 2
    # the two most salient (highest |value_created|) outcomes are outcomes[4] and outcomes[3]
    assert outcomes[4].id in result.replayed_outcome_ids
    assert outcomes[3].id in result.replayed_outcome_ids
    assert outcomes[0].id not in result.replayed_outcome_ids


def test_consolidation_skips_outcomes_with_no_known_edges():
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0)
    attribution = OutcomeAttribution()
    engine = ReplayConsolidationEngine(attribution)
    result = engine.consolidate([outcome], edges_by_outcome={})
    assert result.replayed_outcome_ids == []
    assert result.updated_edges == []


def test_consolidation_generalizes_when_given_a_candidate_pool():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    cited = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    neighbor = _edge(a.id, c.id, "supports", weight=0.5, confidence=0.6)
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0, edge_ids=[cited.id])

    attribution = OutcomeAttribution()
    engine = ReplayConsolidationEngine(attribution)
    result = engine.consolidate(
        [outcome], edges_by_outcome={outcome.action_id: [cited]}, candidate_edges=[neighbor]
    )
    assert str(neighbor.id) in result.generalized_edge_ids
