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
external model (text, numeric/sensor streams). Wiring in a real vision or
audio model later means implementing one more ``PerceptionEncoder``, not
changing this architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

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
