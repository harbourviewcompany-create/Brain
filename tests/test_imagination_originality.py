import pytest

from brain.imagination import ImaginationEngine
from brain.originality_engine import OriginalityEngine


def test_imagination_combines_distinct_memory_refs():
    run = ImaginationEngine().recombine(
        ["memory:permits", "signal:distress", "signal:buyer_intent"],
        ["permits", "distress", "buyer intent"],
    )

    assert run.combination_method == "cross_domain_signal_fusion"
    assert len(run.seed_refs) == 3


def test_originality_rejects_generic_ideas():
    engine = OriginalityEngine()
    with pytest.raises(ValueError, match="generic_idea_rejected"):
        engine.generate(
            title="Generic list dashboard",
            idea="A generic list dashboard for standard AI generated list output.",
            source_signal_refs=["signal:a", "signal:b"],
            memory_refs=["memory:c"],
            combination_method="cross_domain_signal_fusion",
            why_most_people_miss_it="They do not.",
            fastest_test="Run a 48-hour validation.",
            kill_condition="Kill if no replies.",
        )


def test_originality_requires_fastest_test_and_kill_condition():
    idea = OriginalityEngine().generate(
        title="Permit distress buyer lane",
        idea="Combine permit movement, distress evidence and buyer intent into a revenue validation lane for named buyers.",
        source_signal_refs=["signal:permit", "signal:distress"],
        memory_refs=["memory:buyer_intent"],
        combination_method="cross_domain_signal_fusion",
        why_most_people_miss_it="They monitor one dataset at a time and miss the cross-signal buyer.",
        fastest_test="Run a 48-hour validation against 30 named buyers.",
        kill_condition="Kill if no replies after 30 targeted messages.",
    )

    assert idea.novelty_score > 0.5
    assert idea.approval_status == "approval_required"
    assert idea.fastest_test
    assert idea.kill_condition
