from brain.development import DevelopmentTimeline
from brain.self_model import SelfModel, SelfStateSnapshot


def test_development_event_records_before_after_delta():
    model = SelfModel()
    before = model.create_snapshot(current_focus_summary="generic signal watch")
    after = SelfStateSnapshot(
        development_stage="stage_1_functional_consciousness_proxy",
        current_focus_summary="permit-triggered buyer lane",
        changed_since_last_snapshot=True,
        self_assessment="self-state changed from dream insight",
    )
    event = DevelopmentTimeline().record(
        before,
        after,
        cause_refs=["dream:priority_change"],
        priority_deltas={"curiosity": 0.1},
    )

    assert event.before_snapshot_id == before.id
    assert event.after_snapshot_id == after.id
    assert event.priority_deltas["curiosity"] == 0.1
