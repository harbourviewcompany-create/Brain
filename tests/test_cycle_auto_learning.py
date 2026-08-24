from uuid import uuid4

from brain.adapters.learning_store import InMemoryLearningStore
from brain.cycle import CognitiveCycle, CognitiveStimulus
from brain.cycle_learning import (
    attribute_capital_or_result_outcome,
    emit_predictions_for_selected_tasks,
    prediction_for_task,
)
from brain.learning import LearningService
from brain.memory import InMemoryBrainStore
from brain.metabolism import CapitalLedger
from brain.prediction import PredictionStatus
from brain.scheduler import CognitiveTask


def test_prediction_for_task_binds_action_and_utility():
    task = CognitiveTask(
        name="consolidate_observation",
        utility=0.8,
        urgency=0.5,
        novelty=0.2,
        uncertainty_reduction=0.4,
        cost=0.1,
        payload={"belief_id": str(uuid4())},
    )
    pred = prediction_for_task(
        task, belief_id=uuid4(), cycle_id=uuid4(), source_id="sensor-1"
    )
    assert pred.action_id == task.id
    assert abs(pred.expected_value - 0.8) < 1e-9
    assert pred.status is PredictionStatus.OPEN
    assert pred.metadata.get("auto") is True


def test_emit_predictions_writes_ledger_events():
    store = InMemoryBrainStore()
    mem = InMemoryLearningStore()
    learning = LearningService(store, predictions=mem, edges=mem, attributions=mem, sources=mem)
    task = CognitiveTask(
        name="investigate_contradiction",
        utility=0.9,
        urgency=0.9,
        novelty=0.5,
        uncertainty_reduction=0.9,
        cost=0.2,
    )
    mapping = emit_predictions_for_selected_tasks(
        learning, [task], belief_id=None, cycle_id=uuid4(), source_id="ops"
    )
    assert task.id in mapping
    assert mem.get(mapping[task.id]) is not None
    assert any(e.event_type == "prediction.created" for e in store.events)


def test_attribute_capital_outcome_resolves_prediction():
    store = InMemoryBrainStore()
    mem = InMemoryLearningStore()
    learning = LearningService(store, predictions=mem, edges=mem, attributions=mem, sources=mem)
    task = CognitiveTask(
        name="pursue_capital_recovery",
        utility=0.7,
        urgency=1.0,
        novelty=0.0,
        uncertainty_reduction=0.2,
        cost=0.05,
    )
    mapping = emit_predictions_for_selected_tasks(
        learning, [task], belief_id=None, cycle_id=uuid4(), source_id="crm"
    )
    result = attribute_capital_or_result_outcome(
        learning,
        action_id=task.id,
        value_created=1.0,
        open_by_action=mapping,
        source_keys=["crm"],
    )
    assert result.resolution is not None
    assert result.resolution.prediction.status is PredictionStatus.RESOLVED
    kinds = [e.event_type for e in store.events]
    assert "outcome.recorded" in kinds
    assert "prediction.resolved" in kinds
    assert "learning.attribution_recorded" in kinds


def test_cycle_process_auto_predicts_selected_tasks():
    store = InMemoryBrainStore()
    mem = InMemoryLearningStore()
    learning = LearningService(store, predictions=mem, edges=mem, attributions=mem, sources=mem)
    cycle = CognitiveCycle(store, learning=learning, attention_threshold=-10.0)
    result = cycle.process(
        CognitiveStimulus(
            content="Supply link holds",
            source_id="ops",
            claim="Supply link holds",
            source_reliability=0.9,
            supports=True,
            novelty=0.6,
            urgency=0.4,
        )
    )
    assert result.task_ids
    assert any(e.event_type == "prediction.created" for e in store.events)
    assert result.prediction_ids


def test_cycle_capital_outcome_attributes_open_prediction():
    store = InMemoryBrainStore()
    mem = InMemoryLearningStore()
    learning = LearningService(store, predictions=mem, edges=mem, attributions=mem, sources=mem)
    ledger = CapitalLedger(balance=10.0, burn_rate=0.0, survival_threshold=1.0)
    cycle = CognitiveCycle(
        store, learning=learning, capital_ledger=ledger, attention_threshold=-10.0
    )
    r1 = cycle.process(
        CognitiveStimulus(
            content="Pursue recovery",
            source_id="crm",
            claim="Recovery path exists",
            source_reliability=0.8,
            urgency=0.9,
            novelty=0.3,
        )
    )
    assert r1.prediction_ids
    r2 = cycle.process(
        CognitiveStimulus(
            content="Invoice paid",
            source_id="crm",
            claim="Invoice paid",
            source_reliability=0.95,
            capital_outcome_amount=2.5,
            capital_outcome_source="invoice",
            urgency=0.2,
        )
    )
    kinds = [e.event_type for e in store.events]
    assert "outcome.recorded" in kinds or "learning.attribution_recorded" in kinds
    assert r2.attribution_recorded is True or any(
        e.event_type == "learning.attribution_recorded" for e in store.events
    )
