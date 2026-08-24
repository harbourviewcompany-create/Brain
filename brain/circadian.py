"""Circadian and sleep-wake cycling.

``brain/developmental/consolidation.py`` (episodic->semantic compression)
and ``brain/dreaming.py`` (offline recombination) are both real, but both
are manually invoked -- nothing decides *when* the Brain should be doing
new-experience encoding versus consolidating versus dreaming. A real brain
doesn't consolidate memory on demand; it does so because sleep pressure
built up and a sleep-wake cycle gates which mode the system is in.

This models the two-process model of sleep regulation (Borbély): a
homeostatic pressure (Process S) that builds during wake and dissipates
during sleep, combined with a circadian oscillator (Process C) that
independently prefers wake or sleep depending on time-of-day phase.
Within sleep, phase cycles between NREM (favors ``SleepConsolidationService``
-- slow-wave sleep is when hippocampal replay/consolidation actually
happens) and REM (favors ``DreamEngine`` -- REM is when recombination/
hypothesis generation dominates), matching real ultradian sleep-stage
cycling rather than treating "asleep" as one undifferentiated state.

This module only decides *mode* and exposes rate multipliers. It does not
call SleepConsolidationService or DreamEngine itself -- the runner/cycle
layer wires those together, same separation of concerns as
HomeostasisEngine only ever writing to NeuromodulatorState.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

from .cognitive_state import NeuromodulatorState


class CircadianPhase(StrEnum):
    WAKE = "wake"
    NREM = "nrem"
    REM = "rem"


@dataclass(slots=True)
class SleepPressure:
    """Process S. Builds linearly with wake duration and cognitive load,
    dissipates during sleep. Values are unbounded-below-clamped, not
    normalized to [0, 1] internally, but ``ratio`` gives the normalized
    view callers should use for thresholds."""

    level: float = 0.0
    build_rate: float = 0.04
    dissipation_rate: float = 0.10
    saturation: float = 1.0

    def build(self, ticks: float, *, load: float = 1.0) -> SleepPressure:
        self.level = min(self.saturation, self.level + self.build_rate * ticks * max(0.1, load))
        return self

    def dissipate(self, ticks: float) -> SleepPressure:
        self.level = max(0.0, self.level - self.dissipation_rate * ticks)
        return self

    @property
    def ratio(self) -> float:
        return max(0.0, min(1.0, self.level / self.saturation))


@dataclass(slots=True)
class CircadianOscillator:
    """Process C. A single sinusoid over a configurable period standing in
    for the suprachiasmatic-nucleus-driven ~24h rhythm. ``phase_position``
    is in [0, 1) where 0.0 is the trough of the wake drive (biological
    night) and 0.5 is the peak (biological day)."""

    period_ticks: float = 24.0
    phase_position: float = 0.3  # start mid-morning, arbitrary but plausible

    def advance(self, ticks: float) -> CircadianOscillator:
        self.phase_position = (self.phase_position + ticks / self.period_ticks) % 1.0
        return self

    @property
    def wake_drive(self) -> float:
        """[0, 1]; high during biological day, low at biological night."""
        return 0.5 + 0.5 * math.sin(2 * math.pi * (self.phase_position - 0.25))


@dataclass(slots=True)
class CircadianClock:
    """Combines Process S and Process C into a discrete phase, and cycles
    NREM/REM ultradian stages once asleep instead of treating sleep as one
    block. Sleep onset requires *both* high pressure and low circadian
    wake-drive, the same conjunction that governs real sleep-onset latency
    (you can be sleep-deprived and still find it hard to fall asleep at
    the wrong circadian phase, and vice versa)."""

    pressure: SleepPressure = field(default_factory=SleepPressure)
    oscillator: CircadianOscillator = field(default_factory=CircadianOscillator)
    phase: CircadianPhase = CircadianPhase.WAKE
    sleep_onset_pressure: float = 0.65
    wake_threshold_pressure: float = 0.12
    ultradian_period_ticks: float = 1.5
    ticks_since_phase_change: float = 0.0
    cycles_completed_this_sleep: int = 0

    def advance(self, ticks: float, *, cognitive_load: float = 1.0) -> CircadianClock:
        self.oscillator.advance(ticks)
        self.ticks_since_phase_change += ticks

        if self.phase == CircadianPhase.WAKE:
            self.pressure.build(ticks, load=cognitive_load)
            if (
                self.pressure.ratio >= self.sleep_onset_pressure
                and self.oscillator.wake_drive < 0.5
            ):
                self._enter(CircadianPhase.NREM)
        else:
            self.pressure.dissipate(ticks)
            if self.pressure.ratio <= self.wake_threshold_pressure:
                self._enter(CircadianPhase.WAKE)
                self.cycles_completed_this_sleep = 0
            elif self.ticks_since_phase_change >= self.ultradian_period_ticks:
                # REM proportion increases across the sleep episode -- later
                # cycles are more REM-dominant, matching real sleep
                # architecture where REM periods lengthen toward morning.
                if self.phase == CircadianPhase.NREM:
                    self._enter(CircadianPhase.REM)
                else:
                    self.cycles_completed_this_sleep += 1
                    self._enter(CircadianPhase.NREM)

        return self

    def _enter(self, phase: CircadianPhase) -> None:
        self.phase = phase
        self.ticks_since_phase_change = 0.0

    def force_wake(self) -> CircadianClock:
        """Emergency arousal override -- a strong external stimulus should
        be able to wake the Brain even mid-cycle, the way a real alarm
        does. Leaves residual pressure rather than clearing it."""
        self._enter(CircadianPhase.WAKE)
        return self

    @property
    def is_awake(self) -> bool:
        return self.phase == CircadianPhase.WAKE

    def encoding_rate_multiplier(self) -> float:
        """How much new perceptual encoding should proceed. Near-zero
        asleep -- sensory gating during sleep is well established -- not
        exactly zero because arousal-worthy stimuli can still break
        through (which is what force_wake models)."""
        return 1.0 if self.is_awake else 0.05

    def consolidation_rate_multiplier(self) -> float:
        """Slow-wave/NREM sleep is when hippocampal replay and
        systems-level consolidation actually happen."""
        return 1.0 if self.phase == CircadianPhase.NREM else 0.1

    def dream_rate_multiplier(self) -> float:
        """REM is when offline recombination/hypothesis generation
        dominates."""
        return 1.0 if self.phase == CircadianPhase.REM else 0.05

    def modulator_profile(self) -> NeuromodulatorState:
        """Phase-characteristic neuromodulator targets, matching known
        sleep-stage neurochemistry: NREM is low arousal across monoamines
        and ACh; REM is cholinergically active ("REM-on") while aminergic
        (serotonin/norepinephrine) tone drops ("REM-off"); wake is the
        balanced baseline. Callers blend this in the same weighted-average
        style HomeostasisEngine already uses, so circadian state composes
        with affect/homeostasis rather than overwriting them.
        """
        if self.phase == CircadianPhase.WAKE:
            return NeuromodulatorState(
                dopamine=0.5, norepinephrine=0.55, serotonin=0.55,
                acetylcholine=0.55, stress=0.3,
            )
        if self.phase == CircadianPhase.NREM:
            return NeuromodulatorState(
                dopamine=0.3, norepinephrine=0.15, serotonin=0.35,
                acetylcholine=0.2, stress=0.1,
            )
        return NeuromodulatorState(  # REM
            dopamine=0.4, norepinephrine=0.1, serotonin=0.1,
            acetylcholine=0.75, stress=0.15,
        )
