from brain.dreaming import DreamConsolidationEngine


def test_dream_cycle_generates_audited_priority_change():
    cycle, insight = DreamConsolidationEngine().run(
        ["memory:rfp", "memory:permit"],
        ["signal:deadline"],
        ["deadline creates vendor demand"],
    )

    assert cycle.completed_at is not None
    assert insight.dream_cycle_id == cycle.id
    assert insight.requires_review is True
    assert insight.priority_change["curiosity"] > 0
