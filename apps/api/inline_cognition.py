"""Cognition inside the API process, when nothing else is running it.

The Brain's two-process design -- an API that serves reads and a worker that
thinks -- is the right shape, and nothing here replaces it. But a deployment
with no worker is not a Brain that thinks slowly; it is a Brain that has never
had a thought, serving a cockpit that reports it as healthy. The cockpit shows
CYCLE 0 and an unformed belief lattice for exactly as long as no process
anywhere runs the loop.

So the API runs cognition when, and only when, no other process is. Which one
that is gets decided by ``CognitionLease`` rather than by configuration: the
loop starts on whichever process wins a Postgres advisory lock, and every
other process keeps asking. That makes a real worker strictly better than this
without making it required -- deploy one and it takes the lease at the next
yield; take it away and the API resumes thinking. Neither needs to be told
about the other, and there is never more than one writer.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable

from brain.cognition_lease import CognitionLease
from brain.logging_config import get_logger

log = get_logger("inline_cognition")

_DISABLED = {"false", "0", "off", "no"}


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        log.warning("ignoring non-numeric value", extra={"variable": name, "value": raw})
        return default


def cognition_dsn() -> str:
    """The database this process's own store writes to.

    DATABASE_URL first, deliberately, and not the worker DSN the shared worker
    helper prefers. Two reasons, and they point the same way:

    Advisory locks are scoped to a database, not to a role, so the lease must
    be taken in the database the lease-holder actually writes cognition into.
    apps/api/main.py binds its store from DATABASE_URL alone; taking the lock
    somewhere else would let this process and a worker both believe they hold
    a lease nobody shares.

    And BRAIN_WORKER_DATABASE_URL names a trusted-service login that only
    exists once tenant migrations 019+ have been applied. On a deployment held
    at the pre-tenant baseline -- which production is -- that login is not
    there, so preferring it would fail to connect on every attempt and the API
    would never take a lease it is entitled to. The lock grants no access, so
    reaching for the more privileged identity buys nothing here.
    """

    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("BRAIN_WORKER_DATABASE_URL")
        or ""
    ).strip()


def inline_cognition_requested() -> bool:
    """Whether this process should try to think.

    Enabled by default, because the failure it prevents is silent: an operator
    who has to know to switch cognition on is an operator staring at a cockpit
    of zeroes with nothing telling them why. Requires a database either way --
    in-process cognition against the in-memory store would produce beliefs that
    vanish on the next deploy and are invisible to every other reader.
    """

    if (os.environ.get("BRAIN_INLINE_COGNITION") or "").strip().lower() in _DISABLED:
        return False
    return bool(cognition_dsn())


class InlineCognition:
    """A daemon thread that holds the cognition lease and ticks the Brain."""

    def __init__(
        self,
        *,
        tick: Callable[[], Any],
        lease: CognitionLease,
        tick_sleep: float = 1.0,
        retry_seconds: float = 15.0,
        yield_seconds: float = 300.0,
        yield_pause_seconds: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._tick = tick
        self._lease = lease
        self._clock = clock
        self._tick_sleep = tick_sleep
        self._retry_seconds = retry_seconds
        self._yield_seconds = yield_seconds
        self._yield_pause_seconds = yield_pause_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._held_since: float | None = None
        self.ticks = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def holds_lease(self) -> bool:
        return self._held_since is not None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self.run, name="brain-inline-cognition", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=timeout)
        self._release()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self._step()
            except Exception:
                # A thread that dies on one bad tick takes cognition with it
                # and leaves the lease held until the process exits, which is
                # worse than any single failed cycle.
                log.exception("inline cognition step failed")
                self._stop.wait(self._tick_sleep)
        self._release()

    def _step(self) -> None:
        if not self._lease.acquire():
            self._held_since = None
            self._stop.wait(self._retry_seconds)
            return

        if self._held_since is None:
            self._held_since = self._clock()
            log.info("inline cognition acquired the cognition lease")

        if (
            self._yield_seconds > 0
            and self._clock() - self._held_since >= self._yield_seconds
        ):
            # Hand the lease back periodically so a dedicated worker that is
            # blocked waiting for it can take over without anyone restarting
            # this process. If nothing is waiting, we take it straight back.
            self._release()
            self._stop.wait(self._yield_pause_seconds)
            return

        result = self._tick()
        self.ticks += 1
        if not _did_work(result):
            self._stop.wait(self._tick_sleep)

    def _release(self) -> None:
        self._held_since = None
        try:
            self._lease.release()
        except Exception:
            log.exception("inline cognition could not release the cognition lease")


def _did_work(result: Any) -> bool:
    """Whether a tick processed a real stimulus, as opposed to idling.

    Endogenous thought reports no processed items, so an idle Brain sleeps
    between ticks instead of spinning a core on self-generated stimuli.
    """

    if isinstance(result, dict):
        return bool(result.get("processed_this_call"))
    return bool(result)


def start_inline_cognition(tick: Callable[[], Any]) -> InlineCognition | None:
    """Start in-process cognition, or return None if this process should not."""

    if not inline_cognition_requested():
        return None

    lease = CognitionLease(cognition_dsn())
    engine = InlineCognition(
        tick=tick,
        lease=lease,
        tick_sleep=_float_env("BRAIN_TICK_SLEEP", 1.0),
        retry_seconds=_float_env("BRAIN_INLINE_RETRY_SECONDS", 15.0),
        yield_seconds=_float_env("BRAIN_INLINE_YIELD_SECONDS", 300.0),
    )
    engine.start()
    log.info("inline cognition started; waiting for the cognition lease")
    return engine
