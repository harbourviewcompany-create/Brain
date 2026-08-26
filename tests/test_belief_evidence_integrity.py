"""Confidence must track the breadth of evidence, not the volume of submissions.

Two defects motivated these tests:

* repeating one claim from one source walked a belief from 0.5 to certainty in
  three POSTs, because every submission applied a fresh additive nudge; and
* CONTESTED latched forever, because evidence sets only grow and the contested
  branch was evaluated before every confidence threshold -- so one stale
  objection pinned a belief to `contested` at confidence 1.0, and no belief that
  had ever been contested could reach `rejected`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app
from brain.beliefs import BeliefEngine, evidence_fingerprint, rebuild_fingerprints
from brain.domain import Belief, BeliefState, Evidence
from tests.conftest import TEST_API_KEY

client = TestClient(app, headers={"x-api-key": TEST_API_KEY})


def _support(engine: BeliefEngine, belief: Belief, claim: str, source: str, reliability=1.0):
    return engine.apply_evidence(belief, Evidence(claim=claim, source_id=source, reliability=reliability), True)


def _contradict(engine: BeliefEngine, belief: Belief, claim: str, source: str, reliability=1.0):
    return engine.apply_evidence(belief, Evidence(claim=claim, source_id=source, reliability=reliability), False)


# --- deduplication ------------------------------------------------------


def test_repeating_one_claim_does_not_move_confidence():
    engine = BeliefEngine()
    belief = Belief(statement="a market is expanding", confidence=0.5)

    first = _support(engine, belief, "the market grew", "analyst-1", 0.8)
    moved_to = first.confidence
    assert moved_to > 0.5

    repeated = first
    for _ in range(5):
        repeated = _support(engine, repeated, "the market grew", "analyst-1", 0.8)
    assert repeated.confidence == moved_to


def test_repeat_still_records_provenance():
    """A restatement is not new information, but the ledger still shows it."""
    engine = BeliefEngine()
    belief = _support(engine, Belief(statement="s", confidence=0.5), "claim", "src")
    again = _support(engine, belief, "claim", "src")
    assert len(again.supporting_evidence) == 2
    assert len(again.evidence_fingerprints) == 1


def test_same_evidence_object_reapplied_cannot_reach_certainty():
    engine = BeliefEngine()
    belief = Belief(statement="s", confidence=0.5)
    evidence = Evidence(claim="c", source_id="src", reliability=0.8)
    for _ in range(10):
        belief = engine.apply_evidence(belief, evidence, True)
    assert belief.confidence < 0.75
    assert len(belief.supporting_evidence) == 1


def test_fingerprint_ignores_case_and_whitespace():
    a = Evidence(claim="The  Market   Grew", source_id="Analyst-1", reliability=0.5)
    b = Evidence(claim="the market grew", source_id="analyst-1", reliability=0.9)
    assert evidence_fingerprint(a, True) == evidence_fingerprint(b, True)


def test_fingerprint_separates_stance():
    evidence = Evidence(claim="c", source_id="s", reliability=0.5)
    assert evidence_fingerprint(evidence, True) != evidence_fingerprint(evidence, False)


def test_distinct_sources_still_accumulate_with_diminishing_returns():
    engine = BeliefEngine()
    belief = Belief(statement="s", confidence=0.5)
    steps = []
    for i in range(5):
        belief = _support(engine, belief, f"claim-{i}", f"source-{i}", 0.8)
        steps.append(belief.confidence)

    deltas = [b - a for a, b in zip([0.5, *steps], steps)]
    assert all(d > 0 for d in deltas), "independent corroboration must still raise confidence"
    assert deltas == sorted(deltas, reverse=True), "each further item must move less than the last"


# --- state recomputation ------------------------------------------------


def test_contested_resolves_once_one_side_dominates():
    engine = BeliefEngine()
    belief = _contradict(engine, Belief(statement="s", confidence=0.5), "objection", "sceptic")
    for i in range(20):
        belief = _support(engine, belief, f"support-{i}", f"source-{i}")
    assert belief.state is BeliefState.ESTABLISHED


def test_a_belief_that_was_contested_can_still_be_rejected():
    engine = BeliefEngine()
    belief = _support(engine, Belief(statement="s", confidence=0.5), "yes", "a", 0.9)
    for i in range(12):
        belief = _contradict(engine, belief, f"no-{i}", f"sceptic-{i}")
    assert belief.state is BeliefState.REJECTED


def test_genuinely_balanced_evidence_is_contested():
    engine = BeliefEngine()
    belief = _support(engine, Belief(statement="s", confidence=0.5), "yes", "a", 0.9)
    belief = _contradict(engine, belief, "no", "b", 0.9)
    assert belief.state is BeliefState.CONTESTED


def test_contested_holds_while_the_minority_stays_material():
    engine = BeliefEngine()
    belief = Belief(statement="s", confidence=0.5)
    for i in range(3):
        belief = _support(engine, belief, f"yes-{i}", f"pro-{i}")
    for i in range(2):
        belief = _contradict(engine, belief, f"no-{i}", f"con-{i}")
    assert belief.state is BeliefState.CONTESTED


# --- durability ---------------------------------------------------------


def test_fingerprints_rebuild_from_linked_evidence():
    """Stores reconstruct the dedup set on hydrate; it is derived, not stored."""
    engine = BeliefEngine()
    evidence = Evidence(claim="c", source_id="src", reliability=0.8)
    belief = engine.apply_evidence(Belief(statement="s", confidence=0.5), evidence, True)
    after_restart = Belief(
        statement=belief.statement,
        confidence=belief.confidence,
        state=belief.state,
        id=belief.id,
        supporting_evidence=set(belief.supporting_evidence),
        contradicting_evidence=set(belief.contradicting_evidence),
        version=belief.version,
    )
    assert after_restart.evidence_fingerprints == set()

    rebuild_fingerprints(after_restart, {evidence.id: evidence})
    assert after_restart.evidence_fingerprints == belief.evidence_fingerprints

    unchanged = engine.apply_evidence(after_restart, Evidence(claim="c", source_id="src", reliability=0.8), True)
    assert unchanged.confidence == belief.confidence


# --- reachable through the public API -----------------------------------


def test_replaying_one_claim_through_learn_cannot_manufacture_certainty():
    created = client.post(
        "/beliefs",
        json={"statement": "replayed claim integrity", "confidence": 0.5},
    ).json()

    confidences = []
    for _ in range(5):
        response = client.post(
            "/learn",
            json={
                "belief_id": created["id"],
                "claim": "identical claim",
                "source_id": "identical-source",
                "reliability": 0.8,
                "supports": True,
            },
        )
        assert response.status_code == 200
        confidences.append(response.json()["confidence"])

    assert len(set(confidences)) == 1, "replays must not compound"
    assert confidences[0] < 0.85
