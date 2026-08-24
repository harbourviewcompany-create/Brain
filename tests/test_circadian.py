from __future__ import annotations

from brain.circadian import CircadianClock, CircadianOscillator, CircadianPhase, SleepPressure


def test_pressure_builds_while_awake_and_dissipates_while_asleep() -> None:
    pressure = SleepPressure(level=0.0, build_rate=0.1, dissipation_rate=0.2)
    pressure.build(ticks=5.0)
    assert pressure.ratio > 0
    level_after_wake = pressure.level
    pressure.dissipate(ticks=5.0)
    assert pressure.level < level_after_wake


def test_high_pressure_at_circadian_night_triggers_sleep_onset() -> None:
    clock = CircadianClock(
        pressure=SleepPressure(level=0.0, build_rate=0.5, dissipation_rate=0.1),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),  # night trough
        sleep_onset_pressure=0.5,
    )
    assert clock.is_awake
    for _ in range(5):
        clock.advance(ticks=1.0, cognitive_load=1.0)
        if not clock.is_awake:
            break
    assert not clock.is_awake
    assert clock.phase == CircadianPhase.NREM


def test_low_wake_drive_alone_does_not_force_sleep_without_pressure() -> None:
    clock = CircadianClock(
        pressure=SleepPressure(level=0.0, build_rate=0.0, dissipation_rate=0.1),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
    )
    clock.advance(ticks=5.0, cognitive_load=0.0)
    assert clock.is_awake


def test_sleep_cycles_between_nrem_and_rem() -> None:
    clock = CircadianClock(
        pressure=SleepPressure(level=0.9, build_rate=0.5, dissipation_rate=0.02),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
        sleep_onset_pressure=0.5,
        ultradian_period_ticks=1.0,
    )
    clock.advance(ticks=0.1)  # trigger onset
    assert clock.phase == CircadianPhase.NREM
    seen_phases = {clock.phase}
    for _ in range(6):
        clock.advance(ticks=1.0)
        seen_phases.add(clock.phase)
    assert CircadianPhase.REM in seen_phases
    assert CircadianPhase.NREM in seen_phases


def test_wakes_up_once_pressure_dissipates_below_threshold() -> None:
    clock = CircadianClock(
        pressure=SleepPressure(level=0.9, build_rate=0.0, dissipation_rate=0.5),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
        sleep_onset_pressure=0.5,
        wake_threshold_pressure=0.1,
    )
    clock.advance(ticks=0.1)
    assert not clock.is_awake
    for _ in range(20):
        clock.advance(ticks=1.0)
        if clock.is_awake:
            break
    assert clock.is_awake
    assert clock.pressure.ratio <= clock.wake_threshold_pressure + 1e-6


def test_force_wake_overrides_mid_sleep() -> None:
    clock = CircadianClock(
        pressure=SleepPressure(level=0.9, build_rate=0.0, dissipation_rate=0.01),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
        sleep_onset_pressure=0.5,
    )
    clock.advance(ticks=0.1)
    assert not clock.is_awake
    clock.force_wake()
    assert clock.is_awake
    assert clock.pressure.level > 0  # residual pressure, not cleared


def test_rate_multipliers_match_phase() -> None:
    clock = CircadianClock()
    assert clock.encoding_rate_multiplier() == 1.0
    assert clock.consolidation_rate_multiplier() < 1.0
    assert clock.dream_rate_multiplier() < 1.0

    clock.phase = CircadianPhase.NREM
    assert clock.encoding_rate_multiplier() < 1.0
    assert clock.consolidation_rate_multiplier() == 1.0

    clock.phase = CircadianPhase.REM
    assert clock.dream_rate_multiplier() == 1.0


def test_modulator_profile_differs_by_phase() -> None:
    clock = CircadianClock()
    wake_mod = clock.modulator_profile()
    clock.phase = CircadianPhase.REM
    rem_mod = clock.modulator_profile()
    clock.phase = CircadianPhase.NREM
    nrem_mod = clock.modulator_profile()

    # REM: cholinergic-high, aminergic-low ("REM-on"/"REM-off")
    assert rem_mod.acetylcholine > wake_mod.acetylcholine
    assert rem_mod.serotonin < wake_mod.serotonin
    # NREM: globally low arousal
    assert nrem_mod.norepinephrine < wake_mod.norepinephrine
    assert nrem_mod.acetylcholine < wake_mod.acetylcholine
