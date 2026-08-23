from __future__ import annotations

from dataclasses import dataclass

from .cognitive_state import HomeostaticState, NeuromodulatorState


@dataclass(slots=True)
class HomeostasisEngine:
    """Maps system pressure into global modulation without allowing direct goal mutation."""

    stress_gain: float = 0.7

    def regulate(
        self,
        state: HomeostaticState,
        modulation: NeuromodulatorState,
    ) -> NeuromodulatorState:
        stress = state.stress_index
        modulation.stress = (1 - self.stress_gain) * modulation.stress + self.stress_gain * stress
        # High stress raises urgency but suppresses exploration/learning sensitivity.
        modulation.norepinephrine = 0.5 + 0.5 * stress
        modulation.acetylcholine = 0.7 - 0.4 * stress
        modulation.serotonin = 0.7 - 0.3 * stress
        return modulation.clamp()
