from __future__ import annotations

import pytest

from brain.perception import (
    Modality,
    NumericPerceptionEncoder,
    PerceptionService,
    TextPerceptionEncoder,
)


def _service() -> PerceptionService:
    svc = PerceptionService()
    svc.register(TextPerceptionEncoder())
    svc.register(NumericPerceptionEncoder())
    return svc


def test_text_encoder_extracts_valence_proxy_from_lexicon() -> None:
    svc = _service()
    positive = svc.perceive(Modality.TEXT, "ref1", "we saw growth and success and a big win")
    negative = svc.perceive(Modality.TEXT, "ref2", "there was a breach and a risk and a failure")
    assert positive.features["valence_proxy"] > 0
    assert negative.features["valence_proxy"] < 0


def test_unregistered_modality_raises() -> None:
    svc = PerceptionService()
    with pytest.raises(ValueError):
        svc.perceive(Modality.IMAGE, "ref", "content")


def test_repeated_similar_stimulus_habituates_and_novelty_drops() -> None:
    svc = _service()
    first = svc.perceive(Modality.TEXT, "ref1", "quiet steady baseline hum of routine data")
    second = svc.perceive(Modality.TEXT, "ref2", "quiet steady baseline hum of routine data")
    third = svc.perceive(Modality.TEXT, "ref3", "quiet steady baseline hum of routine data")
    assert first.novelty > second.novelty > third.novelty


def test_novel_content_is_not_habituated_by_unrelated_repeats() -> None:
    svc = _service()
    for _ in range(5):
        svc.perceive(Modality.TEXT, "ref", "short text")
    fresh = svc.perceive(Modality.TEXT, "ref_new", "a completely different much longer statement here")
    assert fresh.novelty == 1.0


def test_habituation_recovers_over_time() -> None:
    svc = _service()
    for _ in range(4):
        svc.perceive(Modality.TEXT, "ref", "steady repeated baseline content stream")
    habituated = svc.perceive(Modality.TEXT, "ref", "steady repeated baseline content stream")
    svc.recover(ticks=100.0)
    recovered = svc.perceive(Modality.TEXT, "ref", "steady repeated baseline content stream")
    assert recovered.novelty > habituated.novelty


def test_numeric_encoder_reports_zscore_against_running_stream_stats() -> None:
    svc = _service()
    for value in ["10", "10", "10", "10", "10"]:
        svc.perceive(Modality.NUMERIC, "sensor_a", value)
    outlier = svc.perceive(Modality.NUMERIC, "sensor_a", "1000")
    assert abs(outlier.features["z_score"]) > 3


def test_numeric_and_text_percepts_are_independent_modalities() -> None:
    svc = _service()
    text_percept = svc.perceive(Modality.TEXT, "ref", "growth and success")
    numeric_percept = svc.perceive(Modality.NUMERIC, "sensor", "42")
    assert text_percept.modality == Modality.TEXT
    assert numeric_percept.modality == Modality.NUMERIC
    assert "value" in numeric_percept.features
    assert "valence_proxy" in text_percept.features
