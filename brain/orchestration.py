from __future__ import annotations

from datetime import timedelta

from temporalio import workflow


@workflow.defn
class ContinuousCognitionWorkflow:
    """Replay-safe coordination for long-lived cognition.

    All non-deterministic cognitive work remains in activities. The workflow
    coordinates cadence, prediction maintenance, and history rollover only.
    """

    @workflow.run
    async def run(
        self,
        idle_seconds: float = 1.0,
        maintenance_every: int = 60,
        max_iterations: int = 1000,
        continue_as_new_enabled: bool = True,
    ) -> None:
        idle_ticks = 0
        for _ in range(max_iterations):
            worked = await workflow.execute_activity(
                "brain.cognition_tick",
                start_to_close_timeout=timedelta(minutes=2),
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
                )
                idle_ticks = 0
        if continue_as_new_enabled:
            workflow.continue_as_new(
                args=[idle_seconds, maintenance_every, max_iterations, True]
            )
