"""Temporal worker entry point placeholder.

Production deployment registers durable workflows for sensing, cognition,
dreaming, decay, and outcome feedback. Kept separate from the API so cognition
can continue when no human is using the control plane.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker


async def main() -> None:
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    client = await Client.connect(address, namespace=namespace)
    worker = Worker(client, task_queue="brain-cognition", workflows=[], activities=[])
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
