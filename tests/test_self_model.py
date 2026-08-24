from brain.self_model import SelfModel, SelfModelPhase


def test_self_state_snapshot_tracks_pressure_and_change():
    model = SelfModel()
    snapshot = model.create_snapshot(
        current_focus_summary="permit signals may reveal contractor demand",
        uncertainty_load=0.35,
        contradiction_load=0.2,
        curiosity_pressure=0.6,
        revenue_pressure=0.8,
        risk_pressure=0.25,
    )

    assert snapshot.phase == SelfModelPhase.OBSERVING
    assert snapshot.changed_since_last_snapshot is True
    assert "subjective" not in snapshot.self_assessment.lower()
    assert model.transitions
