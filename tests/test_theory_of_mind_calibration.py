"""Reproducible measurement of theory_of_mind.predict_action() confidence
calibration: does stated confidence track actual accuracy?

This is not a unit test of a single behavior -- it's the acceptance
evidence behind the confidence-formula redesign in
brain/theory_of_mind.py. Calibration was measured empirically (Expected
Calibration Error: mean |confidence - accuracy| across confidence
buckets, weighted by bucket size) across simulated agents of designed-in,
known predictability, run across five fixed random seeds to rule out a
single lucky run. The prior formula (raw goal-match strength scaled by a
trust multiplier) measured ECE around 0.16-0.22. The current formula
(confidence anchored to this agent's own Beta(2,2)-smoothed empirical
accuracy from resolved predictions, lightly modulated by per-prediction
match strength) measures roughly 0.03-0.07 across the same seeds.

The threshold below (0.12) is set with real margin above the worst
observed run of the current formula and well below the best observed run
of the prior formula -- a formula regression back toward the old
behavior would fail this test, not just look worse in a one-off script.
"""

from __future__ import annotations

import random

from brain.theory_of_mind import TheoryOfMindService

_CANDIDATES_A = ["maximize quarterly revenue growth push", "take a long vacation", "ignore the report"]
_CANDIDATES_B = ["explore options broadly", "commit to one plan immediately", "do nothing"]
_CANDIDATES_C = ["reduce operating costs aggressively", "increase headcount", "launch new marketing campaign"]

# Regression threshold: real margin above the worst run observed for the
# current formula (~0.068 at seed 2024) and well below the best run
# observed for the prior, uncalibrated formula (~0.16 at seed 1).
_MAX_ACCEPTABLE_ECE = 0.12


def _run_calibration_trial(seed: int) -> list[tuple[float, bool]]:
    """Runs 120 predict/resolve cycles across three agents with designed-in,
    known predictability (90%, ~33% i.e. chance, 55%), and returns every
    (stated_confidence, was_correct) pair produced. Agents' goals and
    candidate sets are deliberately similar in structure across seeds --
    only the random outcome sequence changes -- so the seed sweep tests
    the formula's stability, not different scenario difficulty."""
    rng = random.Random(seed)
    svc = TheoryOfMindService()
    svc.infer_goal("agent_a", statement="maximize quarterly revenue growth", confidence=0.9, evidence_refs=["e1"])
    svc.infer_goal("agent_b", statement="explore options", confidence=0.5, evidence_refs=["e2"])
    svc.infer_goal("agent_c", statement="reduce operating costs", confidence=0.8, evidence_refs=["e3"])

    results: list[tuple[float, bool]] = []
    for _ in range(40):
        predicted, conf = svc.predict_action("agent_a", _CANDIDATES_A)
        actual = predicted if rng.random() < 0.90 else rng.choice(_CANDIDATES_A)
        rec = svc.record_prediction("agent_a", predicted)
        svc.resolve_prediction("agent_a", rec, actual_action=actual)
        results.append((conf, predicted == actual))

        predicted, conf = svc.predict_action("agent_b", _CANDIDATES_B)
        actual = rng.choice(_CANDIDATES_B)  # fully unpredictable
        rec = svc.record_prediction("agent_b", predicted)
        svc.resolve_prediction("agent_b", rec, actual_action=actual)
        results.append((conf, predicted == actual))

        predicted, conf = svc.predict_action("agent_c", _CANDIDATES_C)
        actual = predicted if rng.random() < 0.55 else rng.choice(_CANDIDATES_C)
        rec = svc.record_prediction("agent_c", predicted)
        svc.resolve_prediction("agent_c", rec, actual_action=actual)
        results.append((conf, predicted == actual))

    return results


def _expected_calibration_error(results: list[tuple[float, bool]], num_bins: int = 5) -> float:
    total = len(results)
    ece = 0.0
    for i in range(num_bins):
        lo, hi = i / num_bins, (i + 1) / num_bins
        bucket = [(c, correct) for c, correct in results if (lo <= c < hi) or (hi == 1.0 and c == 1.0)]
        if not bucket:
            continue
        mean_confidence = sum(c for c, _ in bucket) / len(bucket)
        accuracy = sum(1 for _, correct in bucket if correct) / len(bucket)
        weight = len(bucket) / total
        ece += weight * abs(mean_confidence - accuracy)
    return ece


def test_predict_action_confidence_is_calibrated_across_five_seeds():
    for seed in (42, 1, 7, 99, 2024):
        results = _run_calibration_trial(seed)
        ece = _expected_calibration_error(results)
        assert ece < _MAX_ACCEPTABLE_ECE, (
            f"seed {seed}: Expected Calibration Error {ece:.4f} exceeds "
            f"{_MAX_ACCEPTABLE_ECE} -- predict_action's confidence no "
            f"longer tracks actual accuracy closely enough"
        )


def test_confidence_and_accuracy_are_positively_correlated():
    """A weaker, structural sanity check independent of the ECE
    threshold: across pooled trials from all five seeds, predictions
    stated with higher confidence should, on average, be correct more
    often than predictions stated with lower confidence. This is the
    'directionally informative' property that held even for the OLD,
    uncalibrated formula -- confirms the new formula didn't lose that
    property while fixing the absolute-scale problem."""
    pooled: list[tuple[float, bool]] = []
    for seed in (42, 1, 7, 99, 2024):
        pooled.extend(_run_calibration_trial(seed))

    pooled.sort(key=lambda pair: pair[0])
    midpoint = len(pooled) // 2
    lower_half_accuracy = sum(1 for _, correct in pooled[:midpoint] if correct) / midpoint
    upper_half_accuracy = sum(1 for _, correct in pooled[midpoint:] if correct) / (len(pooled) - midpoint)
    assert upper_half_accuracy > lower_half_accuracy
