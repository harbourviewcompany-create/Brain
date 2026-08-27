"""The cognition lease is what makes 'exactly one writer' true.

Every assertion here is about a way two loops could end up running at once, or
one could end up running none.
"""

from __future__ import annotations

import pytest

from brain.cognition_lease import COGNITION_LOCK_KEY, CognitionLease


class FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConnection:
    def __init__(self, *, granted=True, fail_on=()):
        self.granted = granted
        self.fail_on = tuple(fail_on)
        self.closed = False
        self.statements: list[tuple[str, tuple]] = []

    def execute(self, statement, params=()):
        self.statements.append((statement, params))
        for fragment in self.fail_on:
            if fragment in statement:
                raise RuntimeError(f"boom: {fragment}")
        if "pg_try_advisory_lock" in statement:
            return FakeCursor((self.granted,))
        if "pg_advisory_lock" in statement:
            return FakeCursor((None,))
        return FakeCursor((1,))

    def close(self):
        self.closed = True


def connector(*connections):
    made = list(connections)

    def connect(dsn, autocommit=False):
        assert autocommit is True
        if not made:
            raise AssertionError("more connections requested than the test provided")
        return made.pop(0)

    return connect


def test_acquire_takes_the_lock_and_holds_the_connection_open():
    conn = FakeConnection(granted=True)
    lease = CognitionLease("postgres:///brain", connect=connector(conn))

    assert lease.acquire() is True
    assert lease.held is True
    assert conn.closed is False
    assert conn.statements[0] == ("select pg_try_advisory_lock(%s)", (COGNITION_LOCK_KEY,))


def test_a_denied_lease_closes_its_connection_rather_than_leaking_it():
    conn = FakeConnection(granted=False)
    lease = CognitionLease("postgres:///brain", connect=connector(conn))

    assert lease.acquire() is False
    assert lease.held is False
    # A process that loses the race asks again every few seconds forever; one
    # leaked connection per attempt would exhaust the pool by morning.
    assert conn.closed is True


def test_blocking_acquire_waits_on_the_lock_instead_of_polling_it():
    conn = FakeConnection()
    lease = CognitionLease("postgres:///brain", connect=connector(conn))

    assert lease.acquire(blocking=True) is True
    statement, params = conn.statements[0]
    assert statement == "select pg_advisory_lock(%s)"
    assert params == (COGNITION_LOCK_KEY,)


def test_blocking_acquire_is_not_fooled_by_the_void_return():
    """pg_advisory_lock returns void; reading it as a boolean would report
    every successful blocking acquisition as a failure."""

    conn = FakeConnection()
    lease = CognitionLease("postgres:///brain", connect=connector(conn))

    assert lease.acquire(blocking=True) is True
    assert lease.held is True


def test_release_unlocks_and_closes():
    conn = FakeConnection()
    lease = CognitionLease("postgres:///brain", connect=connector(conn))
    lease.acquire()

    lease.release()

    assert lease.held is False
    assert conn.closed is True
    assert ("select pg_advisory_unlock(%s)", (COGNITION_LOCK_KEY,)) in conn.statements


def test_release_still_closes_when_the_unlock_statement_fails():
    conn = FakeConnection(fail_on=("pg_advisory_unlock",))
    lease = CognitionLease("postgres:///brain", connect=connector(conn))
    lease.acquire()

    lease.release()

    # Closing the session releases the lock even when the explicit unlock
    # cannot be sent, which is why a session-level lock was chosen.
    assert conn.closed is True
    assert lease.held is False


def test_a_held_lease_is_not_revalidated_on_every_tick():
    conn = FakeConnection()
    lease = CognitionLease(
        "postgres:///brain", verify_interval_seconds=3600, connect=connector(conn)
    )
    lease.acquire()
    before = len(conn.statements)

    for _ in range(50):
        assert lease.acquire() is True

    # One round trip per cognitive tick, purely to re-answer a question whose
    # answer cannot have changed, is a needless second of latency per minute.
    assert len(conn.statements) == before


def test_a_severed_connection_is_detected_and_the_lease_re_acquired():
    dead = FakeConnection(fail_on=("select 1",))
    fresh = FakeConnection()
    lease = CognitionLease(
        "postgres:///brain",
        verify_interval_seconds=0,
        connect=connector(dead, fresh),
    )
    assert lease.acquire() is True

    assert lease.acquire() is True

    # Continuing to think on a connection whose lock Postgres has already
    # dropped is exactly the two-writer state this class prevents.
    assert dead.closed is True
    assert fresh.statements[0][0] == "select pg_try_advisory_lock(%s)"


def test_a_closed_connection_is_detected_without_a_round_trip():
    dead = FakeConnection()
    fresh = FakeConnection()
    lease = CognitionLease(
        "postgres:///brain",
        verify_interval_seconds=3600,
        connect=connector(dead, fresh),
    )
    lease.acquire()
    dead.closed = True

    assert lease.acquire() is True
    assert lease.held is True


def test_acquire_reports_failure_rather_than_raising_when_the_database_is_down():
    def refuse(dsn, autocommit=False):
        raise RuntimeError("connection refused")

    lease = CognitionLease("postgres:///brain", connect=refuse)

    # The caller is a loop that must keep retrying; an exception here would
    # kill cognition permanently over a transient outage.
    assert lease.acquire() is False
    assert lease.held is False


def test_release_is_safe_when_the_lease_was_never_held():
    lease = CognitionLease("postgres:///brain", connect=connector())
    lease.release()
    assert lease.held is False


@pytest.mark.parametrize("blocking", [False, True])
def test_every_process_competes_for_the_same_key(blocking):
    conn = FakeConnection()
    lease = CognitionLease("postgres:///brain", connect=connector(conn))
    lease.acquire(blocking=blocking)

    # Two processes using different keys would both believe they hold the
    # lease, which is indistinguishable from having no lease at all.
    assert conn.statements[0][1] == (COGNITION_LOCK_KEY,)
