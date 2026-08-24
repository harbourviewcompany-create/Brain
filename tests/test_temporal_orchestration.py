from __future__ import annotations

import asyncio
from uuid import uuid4

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.worker.main import ContinuousCognitionWorkflow


_activity_counts = {"ticks": 0, "maintenance": 0}


@activity.defn(name="brain.cognition_tick")
async def fake_cognition_tick() -> bool:
    _activity_counts["ticks"] += 1
    return False


@activity.defn(name="brain.prediction_maintenance")
async def fake_prediction_maintenance() -> int:
    _activity_counts["maintenance"] += 1
    return 0


def test_temporal_cognition_workflow_executes_maintenance_and_continue_as_new():
    async def scenario() -> None:
        _activity_counts["ticks"] = 0
        _activity_counts["maintenance"] = 0
        async with await WorkflowEnvironment.start_time_skipping() as env:
            task_queue = f"brain-test-{uuid4()}"
            async with Worker(
                env.client,
                task_queue=task_queue,
                workflows=[ContinuousCognitionWorkflow],
                activities=[fake_cognition_tick, fake_prediction_maintenance],
            ):
                result = await env.client.execute_workflow(
                    ContinuousCognitionWorkflow.run,
                    args=[0.01, 1, 2, 2],
                    id=f"brain-workflow-{uuid4()}",
                    task_queue=task_queue,
                )

        assert result == {"iterations": 2, "maintenance_runs": 2}
        assert _activity_counts == {"ticks": 4, "maintenance": 4}

    asyncio.run(scenario())
