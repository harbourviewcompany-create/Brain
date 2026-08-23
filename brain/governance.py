from dataclasses import dataclass

from .domain import CandidateAction


@dataclass(slots=True)
class GovernanceDecision:
    allowed: bool
    requires_human_approval: bool
    reason: str


class GovernanceGovernor:
    """Hard boundary between internal cognition and consequential external action."""

    def evaluate(self, action: CandidateAction, external_actions_enabled: bool = False) -> GovernanceDecision:
        if action.external and not external_actions_enabled:
            return GovernanceDecision(False, True, "External actions are disabled by system policy.")
        if action.external:
            return GovernanceDecision(True, True, "External action requires explicit human approval.")
        return GovernanceDecision(True, False, "Internal cognitive action is permitted.")
