from uuid import uuid4

from brain.domain import Edge, Node
from brain.generalization import GeneralizationEngine, edge_similarity
from brain.rewiring import RewiringEngine


def _edge(source, target, relation, weight=0.5, confidence=0.5):
    return Edge(source, target, relation, weight=weight, confidence=confidence)


def test_identical_edge_has_similarity_one():
    a = Node("entity", "x")
    b = Node("entity", "y")
    edge = _edge(a.id, b.id, "supports")
    assert edge_similarity(edge, edge) == 1.0


def test_different_relation_has_zero_similarity():
    a, b, c = Node("e", "x"), Node("e", "y"), Node("e", "z")
    e1 = _edge(a.id, b.id, "supports")
    e2 = _edge(a.id, c.id, "contradicts")
    assert edge_similarity(e1, e2) == 0.0


def test_no_shared_endpoint_has_zero_similarity():
    a, b, c, d = Node("e", "w"), Node("e", "x"), Node("e", "y"), Node("e", "z")
    e1 = _edge(a.id, b.id, "supports")
    e2 = _edge(c.id, d.id, "supports")
    assert edge_similarity(e1, e2) == 0.0


def test_shared_endpoint_and_relation_gives_positive_similarity():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    e1 = _edge(a.id, b.id, "supports", confidence=0.6)
    e2 = _edge(a.id, c.id, "supports", confidence=0.6)  # shares node `a`, same confidence
    sim = edge_similarity(e1, e2)
    assert 0.0 < sim <= 1.0
    assert sim == 0.5  # one shared endpoint / 2, confidence perfectly aligned


def test_diverging_confidence_reduces_similarity():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    close = _edge(a.id, b.id, "supports", confidence=0.6)
    aligned = _edge(a.id, c.id, "supports", confidence=0.6)
    diverged = _edge(a.id, c.id, "supports", confidence=0.1)
    assert edge_similarity(close, aligned) > edge_similarity(close, diverged)


def test_propagate_reinforces_similar_edges_with_partial_credit():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    primary = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    neighbor = _edge(a.id, c.id, "supports", weight=0.5, confidence=0.6)
    unrelated = _edge(b.id, c.id, "contradicts", weight=0.5, confidence=0.6)

    engine = GeneralizationEngine(transfer_rate=0.5, similarity_threshold=0.4)
    result = engine.propagate(primary, 0.08, [neighbor, unrelated], RewiringEngine(), uuid4())

    assert len(result.updated_edges) == 1
    assert result.updated_edges[0].id == neighbor.id
    assert result.updated_edges[0].weight > neighbor.weight
    # transferred amount is strictly less than the primary delta it derived from
    assert result.edge_deltas[str(neighbor.id)] < 0.08
    assert str(unrelated.id) not in result.edge_deltas


def test_propagate_weakens_similar_edges_on_negative_delta():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    primary = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    neighbor = _edge(a.id, c.id, "supports", weight=0.5, confidence=0.6)

    engine = GeneralizationEngine(transfer_rate=0.5, similarity_threshold=0.4)
    result = engine.propagate(primary, -0.08, [neighbor], RewiringEngine(), uuid4())

    assert result.updated_edges[0].weight < neighbor.weight


def test_propagate_respects_similarity_threshold():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    primary = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    barely_related = _edge(a.id, c.id, "supports", weight=0.5, confidence=0.05)  # low confidence alignment

    engine = GeneralizationEngine(transfer_rate=0.5, similarity_threshold=0.9)
    result = engine.propagate(primary, 0.08, [barely_related], RewiringEngine(), uuid4())
    assert result.updated_edges == []


def test_propagate_respects_max_neighbors():
    a = Node("e", "source")
    primary = _edge(a.id, Node("e", "p").id, "supports", weight=0.5, confidence=0.6)
    neighbors = [_edge(a.id, Node("e", f"n{i}").id, "supports", weight=0.5, confidence=0.6) for i in range(10)]

    engine = GeneralizationEngine(transfer_rate=0.5, similarity_threshold=0.4, max_neighbors=3)
    result = engine.propagate(primary, 0.08, neighbors, RewiringEngine(), uuid4())
    assert len(result.updated_edges) == 3


def test_propagate_excludes_ids_already_touched_directly():
    a, b, c = Node("e", "source"), Node("e", "claim1"), Node("e", "claim2")
    primary = _edge(a.id, b.id, "supports", weight=0.5, confidence=0.6)
    neighbor = _edge(a.id, c.id, "supports", weight=0.5, confidence=0.6)

    engine = GeneralizationEngine(transfer_rate=0.5, similarity_threshold=0.4)
    result = engine.propagate(
        primary, 0.08, [neighbor], RewiringEngine(), uuid4(), exclude_ids={neighbor.id}
    )
    assert result.updated_edges == []
