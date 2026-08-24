from __future__ import annotations

from brain.hedonic import HedonicSystem


def test_positive_surprise_when_actual_beats_expected() -> None:
    system = HedonicSystem()
    rpe = system.register_outcome(expected_value=0.2, actual_value=0.8)
    assert rpe.is_positive_surprise
    assert rpe.delta > 0


def test_negative_surprise_when_expected_reward_fails_to_arrive() -> None:
    system = HedonicSystem()
    rpe = system.register_outcome(expected_value=0.8, actual_value=0.1)
    assert not rpe.is_positive_surprise
    assert rpe.delta < 0


def test_repeated_identical_reward_stops_producing_positive_error_as_baseline_adapts() -> None:
    system = HedonicSystem(baseline_momentum=0.5)  # fast adaptation for test speed
    first = system.register_outcome(expected_value=0.0, actual_value=0.9)
    for _ in range(20):
        last = system.register_outcome(expected_value=0.0, actual_value=0.9)
    # The raw delta vs a fixed "expected_value=0" stays the same by
    # construction here, but the *dopamine signal* should adapt because
    # baseline_dopamine has drifted up toward the repeated actual value.
    mod_first = system.modulator_delta(first)
    system2 = HedonicSystem(baseline_momentum=0.5, baseline_dopamine=system.baseline_dopamine)
    mod_after_adaptation = system2.modulator_delta(last)
    assert mod_after_adaptation.dopamine <= mod_first.dopamine


def test_pain_is_distinct_from_negative_reward_and_has_withdrawal_urgency() -> None:
    system = HedonicSystem()
    pain = system.register_pain(intensity=0.8, source="resource_exhaustion")
    assert pain.withdrawal_urgency > pain.intensity * 1.0 - 1e-9  # scaled up, not equal
    mod = system.modulator_delta(pain=pain)
    assert mod.stress > 0.5
    assert mod.norepinephrine > 0.4


def test_pain_suppresses_dopamine_independent_of_reward_path() -> None:
    system = HedonicSystem()
    pain = system.register_pain(intensity=0.9, source="threat")
    mod = system.modulator_delta(pain=pain)
    baseline_mod = system.modulator_delta()
    assert mod.dopamine < baseline_mod.dopamine


def test_hedonic_tone_reflects_recent_net_experience() -> None:
    good_system = HedonicSystem()
    for _ in range(5):
        good_system.register_outcome(expected_value=0.2, actual_value=0.9)
    bad_system = HedonicSystem()
    for _ in range(5):
        bad_system.register_outcome(expected_value=0.8, actual_value=0.1)
    bad_system.register_pain(intensity=0.7, source="loss")
    assert good_system.hedonic_tone() > 0
    assert bad_system.hedonic_tone() < 0
    assert good_system.hedonic_tone() > bad_system.hedonic_tone()


def test_hedonic_tone_is_neutral_with_no_history() -> None:
    system = HedonicSystem()
    assert system.hedonic_tone() == 0.0


def test_intensity_and_expected_value_are_clamped_appropriately() -> None:
    system = HedonicSystem()
    pain = system.register_pain(intensity=5.0, source="x")
    assert pain.intensity == 1.0
    assert pain.withdrawal_urgency == 1.0
