import pytest

from brain.developmental.prediction_error import PredictionErrorService


def test_prediction_error_updates_attention() -> None:
    service = PredictionErrorService()
    prediction = service.record_prediction(
        predicted_probability=0.2,
        object_ref="belief:market-demand",
        source_refs=["source:forecast-001"],
    )
    error, trace = service.resolve_prediction(
        prediction,
        actual_outcome=1.0,
        evidence_refs=["outcome:closed-loop-001"],
    )
    pressure = service.create_development_pressure(
        error,
        target="attention:market-demand-signals",
        uncertainty=0.5,
    )

    assert error.absolute_error == pytest.approx(0.8)
    assert pressure.priority == 1.0
    assert pressure.audited_transition == "learning_priority.reweighted_by_prediction_error"
    assert pressure.external_action_triggered is False
    assert "source:forecast-001" in trace.preserved_source_refs


def test_calibration_trace_is_preserved() -> None:
    service = PredictionErrorService()
    prediction = service.record_prediction(
        predicted_probability=0.7,
        object_ref="opportunity:fee-intro",
        source_refs=["source:opportunity-register"],
    )
    error, trace = service.resolve_prediction(
        prediction,
        actual_outcome=0.0,
        evidence_refs=["outcome:no-reply"],
    )

    assert trace.prediction_id == prediction.id
    assert trace.error_id == error.id
    assert trace.prior_probability == 0.7
    assert trace.actual_outcome == 0.0
    assert trace.preserved_source_refs == ["source:opportunity-register", "outcome:no-reply"]


def test_development_pressure_prioritizes_learning() -> None:
    service = PredictionErrorService()
    prediction = service.record_prediction(
        predicted_probability=0.95,
        object_ref="claim:overconfident",
        source_refs=["source:single-weak-signal"],
    )
    error, _ = service.resolve_prediction(
        prediction,
        actual_outcome=0.0,
        evidence_refs=["outcome:failed"],
    )
    pressure = service.create_development_pressure(error, target="calibration", uncertainty=0.2)

    assert pressure.priority > 0.9
    assert service.pressures == [pressure]


def test_prediction_requires_source_refs() -> None:
    service = PredictionErrorService()
    with pytest.raises(ValueError, match="source_refs"):
        service.record_prediction(
            predicted_probability=0.5,
            object_ref="belief:no-source",
            source_refs=[],
        )
