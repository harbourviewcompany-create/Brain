"""Per-tenant service instances must be bounded and built exactly once.

`TenantPartitionedFactory.instances` was an unbounded dict, so a process
accumulated one resident belief-graph projection per tenant it had ever served.
The check-then-set was also unsynchronized: FastAPI runs sync route handlers in
a threadpool, so two concurrent first-requests for one tenant could each build
an instance, and whichever lost the race had its mutations silently discarded.
"""

from __future__ import annotations

import threading
from uuid import uuid4

import pytest

from brain.tenant_context import TenantContext
from brain.tenant_runtime import (
    SYSTEM_PARTITION,
    TenantPartitionedFactory,
    tenant_context_scope,
)


class Counter:
    def __init__(self) -> None:
        self.value = 0
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _context(tenant_id=None) -> TenantContext:
    return TenantContext(tenant_id=tenant_id or uuid4(), actor_id="operator", roles=())


def test_same_tenant_reuses_one_instance():
    factory = TenantPartitionedFactory(Counter, limit=8)
    context = _context()
    with tenant_context_scope(context):
        first = factory.current()
        second = factory.current()
    assert first is second


def test_distinct_tenants_get_distinct_instances():
    factory = TenantPartitionedFactory(Counter, limit=8)
    with tenant_context_scope(_context()):
        a = factory.current()
    with tenant_context_scope(_context()):
        b = factory.current()
    assert a is not b


def test_resident_instances_are_capped():
    factory = TenantPartitionedFactory(Counter, limit=3)
    for _ in range(25):
        with tenant_context_scope(_context()):
            factory.current()
    assert len(factory.instances) <= 3


def test_eviction_is_least_recently_used():
    factory = TenantPartitionedFactory(Counter, limit=2)
    first, second, third = _context(), _context(), _context()

    with tenant_context_scope(first):
        factory.current()
    with tenant_context_scope(second):
        factory.current()
    # Touch the first so the second becomes least recently used.
    with tenant_context_scope(first):
        factory.current()
    with tenant_context_scope(third):
        factory.current()

    keys = set(factory.instances)
    assert str(first.tenant_id) in keys
    assert str(third.tenant_id) in keys
    assert str(second.tenant_id) not in keys


def test_evicted_instances_are_closed():
    factory = TenantPartitionedFactory(Counter, limit=1)
    with tenant_context_scope(_context()):
        first = factory.current()
    with tenant_context_scope(_context()):
        factory.current()
    assert first.closed, "an evicted bundle must release its resources"


def test_system_partition_is_never_evicted():
    factory = TenantPartitionedFactory(Counter, limit=1)
    # No tenant context: this is the legacy/system partition.
    system = factory.current()
    for _ in range(10):
        with tenant_context_scope(_context()):
            factory.current()
    assert SYSTEM_PARTITION in factory.instances
    assert factory.instances[SYSTEM_PARTITION] is system


def test_concurrent_first_requests_build_exactly_one_instance():
    built: list[Counter] = []

    def slow_factory() -> Counter:
        # Widen the window a naive check-then-set would lose in.
        instance = Counter()
        threading.Event().wait(0.01)
        built.append(instance)
        return instance

    factory = TenantPartitionedFactory(slow_factory, limit=8)
    context = _context()
    seen: list[Counter] = []
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        with tenant_context_scope(context):
            seen.append(factory.current())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(built) == 1, "one tenant must not produce competing instances"
    assert len({id(instance) for instance in seen}) == 1


@pytest.mark.parametrize("raw", ["0", "-1", "not-a-number"])
def test_invalid_partition_limit_is_rejected(monkeypatch, raw):
    monkeypatch.setenv("BRAIN_TENANT_BUNDLE_LIMIT", raw)
    with pytest.raises(RuntimeError):
        TenantPartitionedFactory(Counter)


def test_partition_limit_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("BRAIN_TENANT_BUNDLE_LIMIT", "5")
    assert TenantPartitionedFactory(Counter).limit == 5
