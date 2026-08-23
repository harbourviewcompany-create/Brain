from __future__ import annotations

from datetime import timedelta

from temporalio import workflow


@workflow.defn
class ContinuousCognitionWorkflow:
    """Durable cognition heartbeat with replay-safe timers and continue-as-new.

    Cognitive work itself runs in activities. The workflow only coordinates
    cadence, maintenance, retries and history rollover so restarts do not erase
    long-lived cognitive intent.
    """

    @workflow.run
    async def run(
        self,
        idle_seconds: float = 1.0,
        maintenance_every: int = 60,
        max_iterations: int = 1000,
    ) -> None:
        idle_ticks = 0
        for _ in range(max_iterations):
            worked = await workflow.execute_activity(
                "brain.cognition_tick",
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=None,
            )
            if worked:
                idle_ticks = 0
            else:
                idle_ticks += 1
                await workflow.sleep(idle_seconds)
            if idle_ticks >= maintenance_every:
                await workflow.execute_activity(
                    "brain.prediction_maintenance",
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=None,
                )
                idle_ticks = 0
        workflow.continue_as_new(idle_seconds, maintenance_every, max_iterations)
