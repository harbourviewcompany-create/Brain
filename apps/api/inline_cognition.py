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
from math import isfinite
from typing import Any, Callable

from brain.cognition_lease import CognitionLease
from brain.logging_config import get_logger

log = get_logger("inline_cognition")

_DISABLED = {"false", "0", "off", "no"}


def _float_env(name: str, default: float) -> float:
    """A non-negative, finite interval, or the default.

    float() accepts "nan" and "inf", and neither survives contact with this
    loop. Event.wait(Infinity) raises OverflowError -- which, thrown from the
    tick path, escapes into run()'s handler whose own wait raises again, so
    the thread dies without ever releasing the lease and nothing else can take
    over. NaN compares false against everything and turns the pacing sleep
    into a hot retry loop. A negative interval is the same hazard with a
    plainer cause.
    """

    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        parsed = float(raw)
    except ValueError:
        log.warning("ignoring non-numeric value", extra={"variable": name, "value": raw})
        return default
    if not isfinite(parsed) or parsed < 0:
        log.warning(
            "ignoring out-of-range value", extra={"variable": name, "value": raw}
        )
        return default
    return parsed


def tenant_rls_partitioned() -> bool:
    """Whether this deployment routes every read through a tenant context.

    Under BRAIN_TENANT_MODE=required, apps.api.tenant_app rebinds the store
    and heartbeat to tenant-partitioned proxies and resolves the tenant from
    each request. A background thread has no request, so it would select the
    system partition and write brain_events with no brain.tenant_id -- which
    the enforced insert policy rejects, leaving a thread that holds the lease,
    completes no cycles, and blocks a real worker from taking over for the
    length of a yield interval. Inline cognition in a tenant-partitioned
    deployment needs a designed service context; until there is one, it stays
    off and the worker remains the only writer.
    """

    return (os.environ.get("BRAIN_TENANT_MODE") or "").strip().lower() == "required"


def cognition_dsn() -> str:
    """The database this process's own store writes to.

    Advisory locks are scoped to a database, not to a role, so the lease must
    be taken in the database the lease-holder actually writes cognition into.
    apps/api/main.py binds its store from DATABASE_URL alone; taking the lock
    somewhere else would let this process and a worker both believe they hold
    a lease nobody shares.

    There is deliberately no BRAIN_WORKER_DATABASE_URL fallback.
    _configure_from_env() builds the API's durable store from DATABASE_URL
    alone, so a deployment carrying only the worker DSN leaves this process on
    InMemoryBrainStore -- and falling back would take the *worker's* advisory
    lock to protect cognition that is ephemeral and invisible to every reader,
    locking the real worker out of the database it was configured for. That
    login also only exists once tenant migrations 019+ have been applied,
    which on a pre-tenant baseline it has not.
    """

    return (os.environ.get("DATABASE_URL") or "").strip()


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
    if tenant_rls_partitioned():
        log.info("inline cognition stays off in a tenant-partitioned deployment")
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
        on_start: Callable[[], None] | None = None,
        guard: Any | None = None,
    ) -> None:
        self._tick = tick
        self._lease = lease
        self._clock = clock
        self._on_start = on_start
        self._started = False
        # Shared with whatever else in this process may write on the strength
        # of this lease. Its own lock when nothing else does, so the engine is
        # correct standalone.
        self._guard = guard if guard is not None else threading.RLock()
        self._tick_sleep = tick_sleep
        self._retry_seconds = retry_seconds
        self._yield_seconds = yield_seconds
        self._yield_pause_seconds = yield_pause_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._held_since: float | None = None
        #: The lease generation this engine last resumed under. A lease can
        #: reconnect and retake the lock without ever saying so, so ownership
        #: has to be compared by session, not by boolean.
        self._generation: Any = None
        self.ticks = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def holds_lease(self) -> bool:
        return self._held_since is not None

    @property
    def ready_to_write(self) -> bool:
        """Holds the lease *and* has loaded the state it is about to write over.

        Ownership alone is not permission. Between winning the lease and
        finishing ``on_start`` this process is the writer but its belief cache
        still predates whatever the last holder wrote, so anything reasoning
        from it would overwrite beliefs it has never seen. If the resume
        raised, that stays true indefinitely -- so this is what anything
        outside the loop must ask before writing on this engine's ownership.
        """

        return self._held_since is not None and self._started

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
                try:
                    self._stop.wait(self._tick_sleep)
                except Exception:
                    # The recovery path must not be the thing that kills the
                    # thread: an exception raised here escapes the loop
                    # entirely and skips the release below, stranding the
                    # lease on a live connection nothing will ever close.
                    log.exception("inline cognition backoff failed")
                    break
        self._release()

    def revalidate_lease(self) -> bool:
        """Whether the lease is still genuinely this process's, right now.

        holds_lease is a local timestamp and can outlive the connection the
        advisory lock actually lives on. Anything about to write on the
        strength of this engine's ownership has to ask the lease itself.
        """

        try:
            return bool(self._lease.acquire())
        except Exception:
            log.exception("cognition lease could not be revalidated")
            return False

    def _step(self) -> None:
        # Under the guard, because losing or gaining the lease has to be
        # indivisible from the decision to write on it -- otherwise a request
        # can check ownership, and this thread can give it away, in that
        # order, with both believing they are the only writer.
        with self._guard:
            acquired = self._lease.acquire()
            generation = getattr(self._lease, "generation", None)
            if not acquired:
                # Losing the lease is losing currency too: whoever holds it
                # now is writing beliefs this cycle has not seen, so the next
                # acquisition must resume before it thinks.
                self._held_since = None
                self._started = False
            else:
                if generation != self._generation:
                    # A different session behind the same True. acquire()
                    # reconnects and retakes the lock transparently when the
                    # connection has been severed, and in that gap the lock
                    # was free -- long enough for another writer to take it,
                    # write, and hand it back. Comparing only the boolean
                    # reads that as uninterrupted ownership and skips the
                    # resume, which is exactly when the resume matters most.
                    self._generation = generation
                    self._held_since = None
                    self._started = False
                if self._held_since is None:
                    self._held_since = self._clock()
                    log.info("inline cognition acquired the cognition lease")

                if not self._started:
                    # Once per acquisition, not once per process. Only when
                    # the lease is held, because resuming durable state is
                    # preparation for writing and a process that never wins
                    # the race should not do it -- but also every time it is
                    # re-won, because whoever held it in between has been
                    # writing beliefs this cycle cache has never seen.
                    # Skipping it after a yield means reasoning from, and
                    # overwriting, versions that are already stale.
                    #
                    # Inside the guard, and stamped only on success. Releasing
                    # it between the acquisition and the resume let a request
                    # take the same lock, observe ownership truthfully, and
                    # tick against the pre-handover cache -- the very write
                    # this hook exists to prevent, arriving through the one
                    # door the lease cannot guard. And setting the flag first
                    # meant a resume that raised was never retried: the loop
                    # logged, backed off, and then thought on forever from a
                    # cache it had never loaded.
                    if self._on_start is not None:
                        self._on_start()
                    self._started = True

        if not acquired:
            self._stop.wait(self._retry_seconds)
            return

        if (
            self._yield_seconds > 0
            and self._clock() - self._held_since >= self._yield_seconds
        ):
            # Hand the lease back periodically so a dedicated worker that is
            # blocked waiting for it can take over without anyone restarting
            # this process. If nothing is waiting, we take it straight back.
            # Under the guard: a request holding it is mid-tick on the
            # strength of this lease and must finish first.
            with self._guard:
                self._release()
            self._stop.wait(self._yield_pause_seconds)
            return

        result = self._tick()
        self.ticks += 1
        if not _did_work(result):
            self._stop.wait(self._tick_sleep)

    def _release(self) -> None:
        # Every release takes the guard, not only the periodic yield. run()'s
        # final release and stop()'s both used to skip it, so a shutdown
        # landing while a request was inside request_tick() -- ticking on the
        # strength of this very lease -- handed the lock to a waiting worker
        # mid-write. The guard is reentrant, so the yield path that already
        # holds it is unaffected, and stop() joins the loop thread first, so
        # there is nothing left to wait on but an in-flight request, which is
        # precisely what it should wait for.
        with self._guard:
            self._held_since = None
            self._started = False
            self._generation = None
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


def start_inline_cognition(
    tick: Callable[[], Any],
    *,
    on_start: Callable[[], None] | None = None,
    guard: Any | None = None,
) -> InlineCognition | None:
    """Start in-process cognition, or return None if this process should not.

    ``on_start`` runs once, on the thread, after the lease is first won -- the
    place to load durable state the loop is about to reason over.
    """

    if not inline_cognition_requested():
        return None

    lease = CognitionLease(cognition_dsn())
    engine = InlineCognition(
        tick=tick,
        lease=lease,
        on_start=on_start,
        guard=guard,
        tick_sleep=_float_env("BRAIN_TICK_SLEEP", 1.0),
        retry_seconds=_float_env("BRAIN_INLINE_RETRY_SECONDS", 15.0),
        yield_seconds=_float_env("BRAIN_INLINE_YIELD_SECONDS", 300.0),
    )
    engine.start()
    log.info("inline cognition started; waiting for the cognition lease")
    return engine
