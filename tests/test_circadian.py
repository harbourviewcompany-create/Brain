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
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
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
        pressure=SleepPressure(level=0.0, build_rate=0.0),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
        sleep_onset_pressure=0.5,
    )
    clock.advance(ticks=10.0)
    assert clock.is_awake


def test_nrem_rem_ultradian_cycling() -> None:
    clock = CircadianClock(
        pressure=SleepPressure(level=0.9, build_rate=0.0, dissipation_rate=0.01),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
        ultradian_period_ticks=1.0,
        wake_threshold_pressure=0.01,
    )
    clock.phase = CircadianPhase.NREM
    clock.advance(ticks=1.0)
    assert clock.phase == CircadianPhase.REM
    clock.advance(ticks=1.0)
    assert clock.phase == CircadianPhase.NREM


def test_force_wake_leaves_residual_pressure() -> None:
    clock = CircadianClock(pressure=SleepPressure(level=0.8))
    clock.phase = CircadianPhase.NREM
    clock.force_wake()
    assert clock.is_awake
    assert clock.pressure.level > 0


def test_rate_multipliers_match_phase() -> None:
    clock = CircadianClock()
    assert clock.encoding_rate_multiplier() == 1.0
    clock.phase = CircadianPhase.NREM
    assert clock.consolidation_rate_multiplier() == 1.0
    assert clock.encoding_rate_multiplier() < 1.0
    clock.phase = CircadianPhase.REM
    assert clock.dream_rate_multiplier() == 1.0


def test_modulator_profile_differs_by_phase() -> None:
    clock = CircadianClock()
    wake = clock.modulator_profile()
    clock.phase = CircadianPhase.NREM
    nrem = clock.modulator_profile()
    clock.phase = CircadianPhase.REM
    rem = clock.modulator_profile()
    assert nrem.norepinephrine < wake.norepinephrine
    assert rem.acetylcholine > nrem.acetylcholine
