"""Endogenous mind: reasoner, GWT gate, policy, predictions, replay, full loop."""

from __future__ import annotations

from brain.endogenous import (
    ENDOGENOUS_SOURCE_KEY,
    ENDOGENOUS_SOURCE_TYPE,
    EndogenousThoughtGenerator,
    seed_foundational_beliefs,
)
from brain.heartbeat import build_default_heartbeat
from brain.mind_runtime import MindRuntime
from brain.reasoning import LocalHeuristicReasoner, ReasonRequest, default_reasoner


def test_seed_foundational_beliefs_have_unknowns():
    seeds = seed_foundational_beliefs()
    assert len(seeds) >= 3
    assert any(b.unknowns for b in seeds)


def test_local_reasoner_curiosity_and_contradiction():
    r = LocalHeuristicReasoner()
    out = r.reason(
        ReasonRequest(
            task_type="curiosity_answer",
            prompt="Resolve: test",
            context={"question": "Resolve: test", "belief_statements": ["I exist"]},
        )
    )
    assert "Question under investigation" in out.content
    assert out.confidence > 0
    out2 = r.reason(
        ReasonRequest(
            task_type="contradiction",
            prompt="x",
            context={"statement": "s", "supporting": 1, "contradicting": 2, "confidence": 0.4},
        )
    )
    assert "Contested belief" in out2.content


def test_cortex_reasoner_routes():
    cortex = default_reasoner()
    result = cortex.reason(
        ReasonRequest(task_type="dream_skeptic", prompt="h", context={"hypothesis": "A relates to B", "dream_confidence": 0.5})
    )
    assert result.content
    assert "verdict" in (result.metadata or {}) or "Skeptic" in result.content


def test_heartbeat_thinks_with_empty_inbox():
    hb = build_default_heartbeat()
    assert hb.inbox.stats()["pending"] == 0
    seeded = hb.bootstrap_mind()
    snap = hb.tick(max_items=3)
    assert snap["processed_this_call"] >= 1
    assert len(hb._cycle._belief_cache) >= seeded


def test_reasoner_backed_curiosity_answers():
    hb = build_default_heartbeat()
    hb.bootstrap_mind()
    hb.tick(max_items=8)
    st = hb.mind.status()
    assert st["reason_calls"] >= 1 or st["curiosity_resolved"] >= 1


def test_self_model_policy_updates():
    hb = build_default_heartbeat()
    hb.bootstrap_mind()
    hb.tick(max_items=6)
    policy = hb.mind.refresh_policy()
    assert policy.phase != "uninitialized"
    st = hb.mind.status()
    assert "policy" in st


def test_predictions_emitted_with_learning():
    hb = build_default_heartbeat(with_learning=True)
    hb.bootstrap_mind()
    hb.tick(max_items=4)
    events = hb.event_store.read_all()
    preds = [e for e in events if getattr(e, "event_type", None) == "prediction.created"]
    assert len(preds) >= 1


def test_outcome_injection_buffers_for_replay():
    hb = build_default_heartbeat(with_learning=True)
    hb.bootstrap_mind()
    hb.tick(max_items=3)
    result = hb.inject_outcome(value_created=0.8, prediction_accuracy=0.7)
    assert result is not None
    assert hb.mind.status()["outcomes_buffered"] >= 1


def test_night_phase_with_forced_nrem():
    hb = build_default_heartbeat()
    hb.bootstrap_mind()
    from brain.circadian import CircadianPhase

    hb._cycle.circadian.phase = CircadianPhase.NREM
    result = hb.mind.run_night_phase(
        circadian_phase=hb._cycle.circadian.phase,
        beliefs=list(hb._cycle._belief_cache.values()),
        event_store=hb.event_store,
    )
    assert result is not None
    assert result.phase == "nrem"
    events = hb.event_store.read_all()
    assert any(getattr(e, "event_type", None) == "dream.night_phase" for e in events)


def test_gwt_broadcast_and_status():
    mind = MindRuntime()
    item = mind.broadcast_focus(
        title="Focus item",
        content="Content for workspace",
        salience=0.9,
        novelty=0.7,
        urgency=0.6,
    )
    assert item.id in mind.workspace.items
    assert mind.workspace.snapshot()["workspace_items"] >= 1


def test_full_integrated_loop():
    hb = build_default_heartbeat(with_learning=True)
    hb.bootstrap_mind()
    snap = hb.tick(max_items=12)
    assert snap["total_processed"] >= 1
    st = hb.status()
    assert "mind" in st
    assert st["belief_cache_size"] >= 4
    assert st["mind"]["reason_calls"] >= 0
