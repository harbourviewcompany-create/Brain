from uuid import uuid4

from brain.attribution import OutcomeAttribution
from brain.domain import Edge, Node, Outcome
from brain.generalization import GeneralizationEngine
from brain.prediction import PredictionEngine


def _edge(source, target, relation, weight=0.5, confidence=0.5):
    return Edge(source, target, relation, weight=weight, confidence=confidence)


def test_attribute_without_candidate_edges_does_not_generalize():
    """Fully backward compatible: no candidate pool, no propagation."""
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    cited = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    neighbor = _edge(a.id, c.id, "supports", weight=0.5, confidence=0.6)
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0, edge_ids=[cited.id])

    result = OutcomeAttribution().attribute(outcome, edges=[cited])
    assert result.generalized_edge_ids == []
    assert neighbor.weight == 0.5  # untouched, was never even passed in


def test_attribute_with_candidate_edges_generalizes_to_similar_pathway():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    cited = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    neighbor = _edge(a.id, c.id, "supports", weight=0.5, confidence=0.6)
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0, edge_ids=[cited.id])

    attribution = OutcomeAttribution(generalization=GeneralizationEngine(transfer_rate=0.5, similarity_threshold=0.4))
    result = attribution.attribute(outcome, edges=[cited], candidate_edges=[neighbor])

    assert str(neighbor.id) in result.generalized_edge_ids
    updated_neighbor = next(e for e in result.updated_edges if e.id == neighbor.id)
    assert updated_neighbor.weight > neighbor.weight
    # direct update is always strictly larger than the generalized transfer
    direct_delta = result.attribution.edge_deltas[str(cited.id)]
    transferred_delta = result.attribution.edge_deltas[str(neighbor.id)]
    assert transferred_delta < direct_delta


def test_generalization_never_touches_edges_already_directly_cited():
    a, b = Node("e", "source"), Node("e", "claim")
    edge = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    outcome = Outcome(action_id=uuid4(), value_created=1.0, operator_time_cost=0.05, prediction_accuracy=1.0, edge_ids=[edge.id])

    attribution = OutcomeAttribution(generalization=GeneralizationEngine(transfer_rate=0.5, similarity_threshold=0.0))
    # candidate pool includes the same edge that was already directly cited
    result = attribution.attribute(outcome, edges=[edge], candidate_edges=[edge])
    assert result.generalized_edge_ids == []
    assert len(result.updated_edges) == 1  # only the direct update, not double-counted


def test_meta_plasticity_defaults_to_base_rate_with_no_history():
    attribution = OutcomeAttribution(edge_learn_rate=0.08)
    assert attribution.effective_edge_learn_rate == 0.08


def test_meta_plasticity_raises_rate_after_volatile_prediction_errors():
    attribution = OutcomeAttribution(edge_learn_rate=0.08, max_learn_rate=0.5)
    engine = PredictionEngine()
    a, b = Node("e", "x"), Node("e", "y")

    # Feed a sequence that alternates between spot-on and wildly wrong --
    # volatility is the variance of *magnitude*, not sign, so this must
    # swing the size of the error, not just alternate its direction.
    for i in range(6):
        edge = _edge(a.id, b.id, "supports")
        pred = engine.create("x", expected_value=1.0, confidence=0.5)
        outcome = Outcome(
            action_id=uuid4(),
            value_created=1.0 if i % 2 == 0 else -1.0,  # exact, then maximally wrong, alternating
            operator_time_cost=0.05,
            prediction_accuracy=0.0,
            prediction_id=pred.id,
        )
        attribution.attribute(outcome, edges=[edge], prediction=pred)

    assert attribution.effective_edge_learn_rate > 0.08


def test_meta_plasticity_stays_near_base_rate_after_consistently_accurate_predictions():
    attribution = OutcomeAttribution(edge_learn_rate=0.08, max_learn_rate=0.5)
    engine = PredictionEngine()
    a, b = Node("e", "x"), Node("e", "y")

    for _ in range(6):
        edge = _edge(a.id, b.id, "supports")
        pred = engine.create("x", expected_value=1.0, confidence=0.9)
        outcome = Outcome(
            action_id=uuid4(),
            value_created=1.0,  # exactly matches the prediction every time -- zero error
            operator_time_cost=0.05,
            prediction_accuracy=1.0,
            prediction_id=pred.id,
        )
        attribution.attribute(outcome, edges=[edge], prediction=pred)

    assert attribution.effective_edge_learn_rate == attribution.base_edge_learn_rate


def test_meta_plasticity_rate_is_bounded():
    attribution = OutcomeAttribution(edge_learn_rate=0.08, min_learn_rate=0.02, max_learn_rate=0.24)
    engine = PredictionEngine()
    a, b = Node("e", "x"), Node("e", "y")
    for i in range(30):
        edge = _edge(a.id, b.id, "supports")
        pred = engine.create("x", expected_value=1.0, confidence=0.5)
        outcome = Outcome(
            action_id=uuid4(),
            value_created=1.0 if i % 2 == 0 else -1.0,
            operator_time_cost=0.05,
            prediction_accuracy=0.0,
            prediction_id=pred.id,
        )
        attribution.attribute(outcome, edges=[edge], prediction=pred)
    assert attribution.min_learn_rate <= attribution.effective_edge_learn_rate <= attribution.max_learn_rate
    assert attribution.effective_edge_learn_rate == attribution.max_learn_rate  # extreme volatility saturates the cap


def test_meta_plasticity_rate_does_not_leak_into_its_own_update():
    """The rate used for THIS outcome must come from history strictly
    before it -- proven by checking the very first call always uses the
    base rate regardless of how wrong that first prediction turns out to
    be (there is no history yet to have raised the rate)."""
    attribution = OutcomeAttribution(edge_learn_rate=0.08, max_learn_rate=0.5)
    engine = PredictionEngine()
    a, b = Node("e", "x"), Node("e", "y")
    edge = _edge(a.id, b.id, "supports", weight=0.5)
    pred = engine.create("x", expected_value=1.0, confidence=0.9)
    outcome = Outcome(action_id=uuid4(), value_created=0.0, operator_time_cost=0.05, prediction_accuracy=0.0, prediction_id=pred.id)

    result = attribution.attribute(outcome, edges=[edge], prediction=pred)
    used_rate = float(result.attribution.rationale[4].split("=")[1])
    assert used_rate == 0.08
