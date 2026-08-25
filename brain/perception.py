"""Sensory perception encoding.

``brain/adapters/cognition.py`` has ``PostgresSensoryInbox`` -- a durable
queue for stimuli waiting to be processed. That's plumbing, not
perception: nothing turns raw content into a structured percept with
extracted features, salience, and novelty the way an actual sensory
system does. And nothing modeled sensory adaptation/habituation -- the
basic fact that a repeated, unchanging stimulus produces a progressively
weaker perceptual response (this is why you stop noticing a hum in the
room, and it's a real, separate mechanism from the top-down attention
scoring already implemented in ``brain/attention.py``).

This module is deliberately modality-pluggable rather than claiming to
solve vision or audio: ``PerceptionEncoder`` is the interface, and this
file ships concrete encoders for the modalities that don't require an
external model (text, numeric/sensor streams, and image/audio via
classical signal-processing features). Wiring in a deep-learning-based
vision or audio model later means implementing one more
``PerceptionEncoder``, not changing this architecture.

The image/audio encoders here are deliberately scoped to early-
sensory-cortex-style feature extraction (luminance/edge statistics for
vision, amplitude/frequency statistics for audio) rather than semantic
understanding -- this is an honest analog of what V1/A1 actually compute
before higher visual/auditory areas get involved, not a substitute for a
real object/scene/speech recognition model. No network access or model
weights required; numpy and Pillow's decoders are the only dependencies.
"""

from __future__ import annotations

import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

import numpy as np
from PIL import Image

from .domain import utcnow


class Modality(StrEnum):
    TEXT = "text"
    NUMERIC = "numeric"
    STRUCTURED = "structured"
    IMAGE = "image"
    AUDIO = "audio"


@dataclass(slots=True)
class Percept:
    """The output of perception: not raw content, features extracted from
    it, plus how novel/salient it is against recent sensory history."""

    modality: Modality
    raw_ref: str
    features: dict[str, float]
    novelty: float  # [0, 1]; habituation-adjusted, not just first-time novelty
    id: UUID = field(default_factory=uuid4)
    encoded_at: object = field(default_factory=utcnow)


_POSITIVE_LEXICON = {"gain", "win", "growth", "opportunity", "success", "improved", "resolved"}
_NEGATIVE_LEXICON = {"loss", "fail", "risk", "threat", "breach", "delay", "error", "blocked"}


class PerceptionEncoder(ABC):
    """One sensory modality's transducer: raw content -> feature vector.
    Deliberately narrow -- an encoder's only job is feature extraction.
    Habituation and novelty live in ``PerceptionService`` so every
    modality gets adaptation for free instead of reimplementing it.
    """

    modality: Modality

    @abstractmethod
    def encode(self, raw_ref: str, content: str) -> dict[str, float]:
        ...

    @abstractmethod
    def similarity_key(self, features: dict[str, float]) -> tuple:
        """A coarse bucket used to detect 'basically the same stimulus
        again' for habituation, without needing full feature-vector
        distance for every modality."""
        ...


class TextPerceptionEncoder(PerceptionEncoder):
    modality = Modality.TEXT

    def encode(self, raw_ref: str, content: str) -> dict[str, float]:
        tokens = content.lower().split()
        length = float(len(tokens))
        pos_hits = sum(1 for t in tokens if t.strip(".,!?") in _POSITIVE_LEXICON)
        neg_hits = sum(1 for t in tokens if t.strip(".,!?") in _NEGATIVE_LEXICON)
        valence_proxy = 0.0
        if pos_hits or neg_hits:
            valence_proxy = (pos_hits - neg_hits) / (pos_hits + neg_hits)
        return {
            "length": length,
            "lexical_diversity": len(set(tokens)) / length if length else 0.0,
            "valence_proxy": valence_proxy,
            "pos_hits": float(pos_hits),
            "neg_hits": float(neg_hits),
        }

    def similarity_key(self, features: dict[str, float]) -> tuple:
        return (round(features["length"] / 5) * 5, round(features["valence_proxy"], 1))


class NumericPerceptionEncoder(PerceptionEncoder):
    """For sensor-style scalar streams -- metrics, prices, telemetry.
    Tracks a running mean/variance so features are reported as
    z-scores against the stream's own recent history, not raw magnitude."""

    modality = Modality.NUMERIC

    def __init__(self) -> None:
        self._mean = 0.0
        self._var = 1.0
        self._n = 0

    def _update_running_stats(self, value: float) -> None:
        self._n += 1
        delta = value - self._mean
        self._mean += delta / self._n
        delta2 = value - self._mean
        self._var = ((self._n - 1) * self._var + delta * delta2) / self._n

    def encode(self, raw_ref: str, content: str) -> dict[str, float]:
        value = float(content)
        # Surprise is judged against the distribution *before* this point
        # is folded in -- otherwise an outlier partially explains itself
        # away by widening the variance it's being compared against.
        prior_mean = self._mean
        prior_std = max(1e-6, self._var ** 0.5)
        z = (value - prior_mean) / prior_std
        self._update_running_stats(value)
        return {"value": value, "z_score": z, "running_mean": self._mean}

    def similarity_key(self, features: dict[str, float]) -> tuple:
        return (round(features["z_score"], 1),)


class ImagePerceptionEncoder(PerceptionEncoder):
    """Early-visual-cortex-style feature extraction: luminance and edge
    statistics, not object recognition. ``content`` is a filesystem path
    to an image file (any format Pillow can decode)."""

    modality = Modality.IMAGE

    def encode(self, raw_ref: str, content: str) -> dict[str, float]:
        with Image.open(content) as img:
            width, height = img.size
            gray = np.asarray(img.convert("L"), dtype=np.float64)
            rgb = np.asarray(img.convert("RGB"), dtype=np.float64)

        brightness_mean = float(gray.mean())
        brightness_std = float(gray.std())

        # Crude gradient-magnitude edge density -- the same first
        # derivative that simple-cell receptive fields in V1 compute,
        # not a full Sobel/Canny pipeline.
        grad_y = np.abs(np.diff(gray, axis=0))
        grad_x = np.abs(np.diff(gray, axis=1))
        edge_density = float((grad_y.mean() + grad_x.mean()) / 2.0)

        color_variance = float(rgb.std(axis=(0, 1)).mean())

        return {
            "width": float(width),
            "height": float(height),
            "aspect_ratio": float(width) / float(height) if height else 0.0,
            "brightness_mean": brightness_mean,
            "brightness_std": brightness_std,
            "edge_density": edge_density,
            "color_variance": color_variance,
        }

    def similarity_key(self, features: dict[str, float]) -> tuple:
        return (round(features["brightness_mean"] / 10) * 10, round(features["edge_density"] / 5) * 5)


class AudioPerceptionEncoder(PerceptionEncoder):
    """Early-auditory-cortex-style feature extraction: amplitude and
    frequency statistics, not speech/sound recognition. ``content`` is a
    filesystem path to a mono or stereo PCM WAV file."""

    modality = Modality.AUDIO

    def encode(self, raw_ref: str, content: str) -> dict[str, float]:
        with wave.open(content, "rb") as wf:
            n_frames = wf.getnframes()
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            raw = wf.readframes(n_frames)

        dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(sample_width, np.int16)
        samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1)

        max_amplitude = float(np.iinfo(dtype).max)
        normalized = samples / max_amplitude if max_amplitude else samples

        rms_amplitude = float(np.sqrt(np.mean(normalized**2))) if normalized.size else 0.0

        # Zero-crossing rate: a cheap, classical proxy for dominant
        # frequency/pitch, the same signal early auditory processing is
        # sensitive to before any tonotopic frequency decomposition.
        signs = np.sign(normalized)
        signs[signs == 0] = 1
        zero_crossings = np.count_nonzero(np.diff(signs))
        zero_crossing_rate = float(zero_crossings) / len(normalized) if len(normalized) > 1 else 0.0

        # Spectral centroid via a plain FFT -- the "brightness" of the
        # sound, mirroring the tonotopic (frequency-to-place) map in A1
        # at a coarse, single-number level.
        spectral_centroid = 0.0
        if normalized.size > 1:
            spectrum = np.abs(np.fft.rfft(normalized))
            freqs = np.fft.rfftfreq(len(normalized), d=1.0 / sample_rate)
            total_energy = spectrum.sum()
            if total_energy > 0:
                spectral_centroid = float((freqs * spectrum).sum() / total_energy)

        duration_seconds = float(n_frames) / sample_rate if sample_rate else 0.0

        return {
            "duration_seconds": duration_seconds,
            "rms_amplitude": rms_amplitude,
            "zero_crossing_rate": zero_crossing_rate,
            "spectral_centroid": spectral_centroid,
        }

    def similarity_key(self, features: dict[str, float]) -> tuple:
        return (
            round(features["spectral_centroid"] / 100) * 100,
            round(features["rms_amplitude"], 1),
        )


@dataclass
class PerceptionService:
    """Runs content through the right encoder and applies habituation:
    repeated stimuli in the same similarity bucket produce progressively
    lower novelty, recovering over time/absence the way real sensory
    adaptation does. This composes with brain/attention.py's
    AttentionMarket -- novelty here feeds that scoring input rather than
    replacing it.
    """

    encoders: dict[Modality, PerceptionEncoder] = field(default_factory=dict)
    _habituation: dict[tuple, float] = field(default_factory=dict)  # key -> exposure count
    habituation_rate: float = 0.25
    recovery_rate: float = 0.05

    def register(self, encoder: PerceptionEncoder) -> None:
        self.encoders[encoder.modality] = encoder

    def perceive(self, modality: Modality, raw_ref: str, content: str) -> Percept:
        if modality not in self.encoders:
            raise ValueError(f"no_encoder_registered_for_modality:{modality}")
        encoder = self.encoders[modality]
        features = encoder.encode(raw_ref, content)
        key = (modality,) + encoder.similarity_key(features)

        exposure = self._habituation.get(key, 0.0)
        novelty = max(0.0, 1.0 - self.habituation_rate * exposure)
        self._habituation[key] = exposure + 1.0

        return Percept(modality=modality, raw_ref=raw_ref, features=features, novelty=novelty)

    def recover(self, ticks: float = 1.0) -> None:
        """Habituation fades with time/absence of the stimulus -- called
        from the same tick loop that drives HomeostasisEngine/
        CircadianClock, so a stimulus not seen in a while regains novelty
        rather than staying permanently suppressed."""
        for key in list(self._habituation.keys()):
            self._habituation[key] = max(0.0, self._habituation[key] - self.recovery_rate * ticks)
            if self._habituation[key] <= 0.0:
                del self._habituation[key]
