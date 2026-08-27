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

    @property
    def held(self) -> bool:
        return self._conn is not None

    def acquire(self, *, blocking: bool = False) -> bool:
        """Take the lease, or report that another process holds it.

        When the lease is already held this revalidates the connection at most
        every ``verify_interval_seconds``: a connection can be severed without
        either side noticing, and a holder that keeps thinking on a dead
        connection has silently become a second writer.
        """

        if self._conn is not None:
            if self._still_connected():
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

    def _still_connected(self) -> bool:
        conn = self._conn
        if conn is None:
            return False
        if getattr(conn, "closed", False):
            return False
        now = time.monotonic()
        if now - self._verified_at < self._verify_interval:
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
