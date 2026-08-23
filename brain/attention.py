from dataclasses import dataclass


@dataclass(slots=True)
class AttentionSignal:
    commercial_upside: float
    novelty: float
    urgency: float
    contradiction_value: float
    source_quality: float
    uncertainty_reduction: float
    noise_probability: float
    operator_burden: float


class AttentionMarket:
    """Allocates finite cognitive budget instead of processing all stimuli equally."""

    def score(self, s: AttentionSignal) -> float:
        positive = (
            1.4 * s.commercial_upside
            + 1.1 * s.novelty
            + 1.0 * s.urgency
            + 1.2 * s.contradiction_value
            + 0.9 * s.source_quality
            + 1.1 * s.uncertainty_reduction
        )
        negative = 1.2 * s.noise_probability + 0.8 * s.operator_burden
        return positive - negative
