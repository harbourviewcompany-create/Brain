from __future__ import annotations

import wave

import numpy as np
import pytest
from PIL import Image

from brain.perception import AudioPerceptionEncoder, ImagePerceptionEncoder, Modality, PerceptionService


@pytest.fixture
def bright_image_path(tmp_path):
    path = tmp_path / "bright.png"
    arr = np.full((32, 32, 3), 230, dtype=np.uint8)
    Image.fromarray(arr).save(path)
    return str(path)


@pytest.fixture
def dark_image_path(tmp_path):
    path = tmp_path / "dark.png"
    arr = np.full((32, 32, 3), 20, dtype=np.uint8)
    Image.fromarray(arr).save(path)
    return str(path)


@pytest.fixture
def high_edge_image_path(tmp_path):
    path = tmp_path / "checkerboard.png"
    arr = np.zeros((32, 32, 3), dtype=np.uint8)
    arr[::2, ::2] = 255
    arr[1::2, 1::2] = 255
    Image.fromarray(arr).save(path)
    return str(path)


def _write_wav(path, freq_hz, duration_s=0.5, sample_rate=8000, amplitude=0.5):
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    tone = (amplitude * np.sin(2 * np.pi * freq_hz * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(tone.tobytes())


@pytest.fixture
def low_tone_wav_path(tmp_path):
    path = tmp_path / "low.wav"
    _write_wav(path, freq_hz=220)
    return str(path)


@pytest.fixture
def high_tone_wav_path(tmp_path):
    path = tmp_path / "high.wav"
    _write_wav(path, freq_hz=3000)
    return str(path)


@pytest.fixture
def silent_wav_path(tmp_path):
    path = tmp_path / "silence.wav"
    _write_wav(path, freq_hz=440, amplitude=0.0)
    return str(path)


def _service():
    svc = PerceptionService()
    svc.register(ImagePerceptionEncoder())
    svc.register(AudioPerceptionEncoder())
    return svc


def test_bright_and_dark_images_are_distinguished_by_brightness(bright_image_path, dark_image_path):
    svc = _service()
    bright = svc.perceive(Modality.IMAGE, "ref1", bright_image_path)
    dark = svc.perceive(Modality.IMAGE, "ref2", dark_image_path)
    assert bright.features["brightness_mean"] > dark.features["brightness_mean"]


def test_checkerboard_has_higher_edge_density_than_flat_image(bright_image_path, high_edge_image_path):
    svc = _service()
    flat = svc.perceive(Modality.IMAGE, "flat", bright_image_path)
    checkerboard = svc.perceive(Modality.IMAGE, "checker", high_edge_image_path)
    assert checkerboard.features["edge_density"] > flat.features["edge_density"]


def test_image_features_include_dimensions(bright_image_path):
    svc = _service()
    percept = svc.perceive(Modality.IMAGE, "ref", bright_image_path)
    assert percept.features["width"] == 32.0
    assert percept.features["height"] == 32.0
    assert percept.features["aspect_ratio"] == pytest.approx(1.0)


def test_repeated_identical_image_habituates(bright_image_path):
    svc = _service()
    first = svc.perceive(Modality.IMAGE, "ref1", bright_image_path)
    second = svc.perceive(Modality.IMAGE, "ref2", bright_image_path)
    assert first.novelty > second.novelty


def test_low_and_high_tone_are_distinguished_by_spectral_centroid(low_tone_wav_path, high_tone_wav_path):
    svc = _service()
    low = svc.perceive(Modality.AUDIO, "low", low_tone_wav_path)
    high = svc.perceive(Modality.AUDIO, "high", high_tone_wav_path)
    assert high.features["spectral_centroid"] > low.features["spectral_centroid"]


def test_silence_has_near_zero_rms_amplitude(silent_wav_path):
    svc = _service()
    percept = svc.perceive(Modality.AUDIO, "silence", silent_wav_path)
    assert percept.features["rms_amplitude"] < 0.01


def test_audio_duration_matches_wav_file(low_tone_wav_path):
    svc = _service()
    percept = svc.perceive(Modality.AUDIO, "ref", low_tone_wav_path)
    assert percept.features["duration_seconds"] == pytest.approx(0.5, abs=0.01)


def test_repeated_identical_tone_habituates(low_tone_wav_path):
    svc = _service()
    first = svc.perceive(Modality.AUDIO, "ref1", low_tone_wav_path)
    second = svc.perceive(Modality.AUDIO, "ref2", low_tone_wav_path)
    assert first.novelty > second.novelty


def test_image_and_audio_are_independent_modalities_in_shared_service(bright_image_path, low_tone_wav_path):
    svc = _service()
    img = svc.perceive(Modality.IMAGE, "ref", bright_image_path)
    audio = svc.perceive(Modality.AUDIO, "ref2", low_tone_wav_path)
    assert img.modality == Modality.IMAGE
    assert audio.modality == Modality.AUDIO
    assert "brightness_mean" in img.features
    assert "spectral_centroid" in audio.features
