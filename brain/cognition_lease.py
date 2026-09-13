"""Single-writer lease for the cognition loop.

Exactly one process per database may drive cognition. Two loops sharing an
event store would double every ``cycle.completed``, race on belief versions,
and make the cockpit's counters meaningless -- and the counters are how the
Observatory now reports whether the Brain is thinking at all.

The lease is a Postgres *session-level* advisory lock, which is the right
primitive here for one reason: it dies with its connection. A crashed worker,
a redeployed API container, a killed process -- none of them can strand the
lease, because the moment the backend goes away Postgres drops the lock. No
heartbeat table, no expiry sweeper, no stale-lock recovery path to get wrong.
"""

from __future__ import annotations

import time
from typing import Any

import psycopg

from brain.logging_config import get_logger

log = get_logger("cognition_lease")

# Arbitrary fixed key. Any process that asks for this key competes for the
# same lease; changing it in one process and not another silently re-permits
# two concurrent cognition loops, which is the failure this module exists to
# prevent.
COGNITION_LOCK_KEY = 728_141_003


class CognitionLease:
    """The right to run cognition against one database.

    ``acquire`` is non-blocking by default: a process that loses the race
    should stay alive and keep asking rather than exit, so that it takes over
    the instant the current holder goes away.
    """

    def __init__(
        self,
        dsn: str,
        *,
        key: int = COGNITION_LOCK_KEY,
        verify_interval_seconds: float = 30.0,
        connect: Any | None = None,
    ) -> None:
        self._dsn = dsn
        self._key = key
        self._verify_interval = verify_interval_seconds
        self._connect = connect or psycopg.connect
        self._conn: Any | None = None
        self._verified_at: float = 0.0
        self._generation = 0

    @property
    def held(self) -> bool:
        return self._conn is not None

    @property
    def generation(self) -> int:
        """How many times this lease has been taken on a *new* connection.

        acquire() returning True does not mean ownership was continuous. When
        the connection has been severed it reconnects and takes the lock
        again, transparently -- and in the gap between those two moments the
        lock was free, so another process could take it, write, and release
        it. To a caller comparing booleans that is indistinguishable from
        never having let go, which is how a holder resumes from a belief
        cache that is several versions stale.

        This counter changes exactly when the underlying session does, so a
        caller can tell a re-acquisition from uninterrupted ownership and
        reload durable state before writing again.
        """

        return self._generation

    def acquire(self, *, blocking: bool = False, verify: bool = False) -> bool:
        """Take the lease, or report that another process holds it.

        When the lease is already held this revalidates the connection at most
        every ``verify_interval_seconds``: a connection can be severed without
        either side noticing, and a holder that keeps thinking on a dead
        connection has silently become a second writer.

        ``verify`` skips that interval and probes the socket now. Callers about
        to write must pass it: inside the interval a dead connection still
        answers True from cache, while Postgres dropped the advisory lock the
        moment the backend went away -- so another process can hold the lock,
        legitimately, for up to verify_interval_seconds while this one goes on
        writing under a lock it no longer has. The probe is a `select 1` on an
        already-open connection, which is nothing beside the cycle it guards.
        """

        if self._conn is not None:
            if self._still_connected(force=verify):
                return True
            log.warning("cognition lease connection lost; re-acquiring")
            self._drop()

        try:
            conn = self._connect(self._dsn, autocommit=True)
        except Exception:
            log.exception("cognition lease could not open a connection")
            return False

        statement = (
            "select pg_advisory_lock(%s)"
            if blocking
            else "select pg_try_advisory_lock(%s)"
        )
        try:
            row = conn.execute(statement, (self._key,)).fetchone()
        except Exception:
            log.exception("cognition lease could not be requested")
            self._close(conn)
            return False

        # pg_advisory_lock returns void, not a boolean: reaching this line at
        # all means the blocking wait completed and the lock is ours.
        granted = True if blocking else bool(row and row[0])
        if not granted:
            self._close(conn)
            return False

        self._conn = conn
        self._verified_at = time.monotonic()
        # A new session, and so a new generation: whatever happened while this
        # process was disconnected, it did not happen under this lock.
        self._generation += 1
        return True

    def release(self) -> None:
        """Give the lease up so a waiting process can take it."""

        if self._conn is None:
            return
        conn, self._conn = self._conn, None
        try:
            conn.execute("select pg_advisory_unlock(%s)", (self._key,))
        except Exception:
            # Closing the connection releases the lock regardless, which is
            # the whole reason a session-level lock was chosen.
            log.warning("cognition lease unlock failed; closing to release")
        self._close(conn)

    def _still_connected(self, *, force: bool = False) -> bool:
        conn = self._conn
        if conn is None:
            return False
        if getattr(conn, "closed", False):
            return False
        now = time.monotonic()
        if not force and now - self._verified_at < self._verify_interval:
            return True
        try:
            conn.execute("select 1")
        except Exception:
            return False
        self._verified_at = now
        return True

    def _drop(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            self._close(conn)

    @staticmethod
    def _close(conn: Any) -> None:
        try:
            conn.close()
        except Exception:
            log.debug("cognition lease connection close failed", exc_info=True)
