from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


DEFAULT_STORAGE_BUDGET_BYTES = 5 * 1024 * 1024 * 1024


class StoragePressure(StrEnum):
    NORMAL = "normal"
    COMPACT = "compact"
    AGGRESSIVE_COMPACTION = "aggressive_compaction"
    THROTTLE_OPTIONAL = "throttle_optional"
    REFUSE_OPTIONAL = "refuse_optional"


@dataclass(frozen=True, slots=True)
class StoragePolicy:
    """Hard guardrails for a finite $0 storage budget.

    Canonical cognitive events are never silently discarded. Pressure controls
    target physical compaction and explicitly optional telemetry only.
    """

    budget_bytes: int = DEFAULT_STORAGE_BUDGET_BYTES
    compact_at: float = 0.60
    aggressive_at: float = 0.70
    throttle_optional_at: float = 0.80
    refuse_optional_at: float = 0.85

    def utilization(self, used_bytes: int) -> float:
        if self.budget_bytes <= 0:
            raise ValueError("storage budget must be positive")
        return max(0.0, used_bytes / self.budget_bytes)

    def pressure(self, used_bytes: int) -> StoragePressure:
        ratio = self.utilization(used_bytes)
        if ratio >= self.refuse_optional_at:
            return StoragePressure.REFUSE_OPTIONAL
        if ratio >= self.throttle_optional_at:
            return StoragePressure.THROTTLE_OPTIONAL
        if ratio >= self.aggressive_at:
            return StoragePressure.AGGRESSIVE_COMPACTION
        if ratio >= self.compact_at:
            return StoragePressure.COMPACT
        return StoragePressure.NORMAL

    def optional_writes_allowed(self, used_bytes: int) -> bool:
        return self.pressure(used_bytes) is not StoragePressure.REFUSE_OPTIONAL
