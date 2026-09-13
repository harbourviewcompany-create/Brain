from __future__ import annotations

from brain.money_spine import MoneySpineService, RevenueSignal


class AtomicStore:
    def __init__(self):
        self.atomic_calls = 0
        self.signals = {}
        self.scores = {}

    def load_lanes(self):
        return {}

    def seed_lanes(self, lanes):
        self.lanes = {lane.lane_id: lane for lane in lanes}

    def load_source_scores(self):
        return {}

    def save_signal_and_score(self, signal, scored):
        self.atomic_calls += 1
        self.signals[signal.id] = signal
        self.scores[scored.id] = scored

    def save_signal(self, signal):
        raise AssertionError("non-atomic signal write used")

    def save_scored_opportunity(self, scored):
        raise AssertionError("non-atomic score write used")


def test_money_spine_prefers_atomic_signal_score_store_operation():
    store = AtomicStore()
    service = MoneySpineService(store=store)
    signal = RevenueSignal(
        raw_signal="atomic contract",
        source_id="atomic-source",
        money_lane_id="high_intent_lead_pack",
        evidence_refs=["https://example.test/atomic"],
        named_buyer="Buyer",
        decision_maker="Operator",
        visible_pain="urgent",
        urgency_reason="now",
        payment_path="approved manual action",
        contact_channel="buyer@example.test",
    )
    scored = service.score_signal(signal)
    assert store.atomic_calls == 1
    assert signal.id in store.signals
    assert scored.id in store.scores
