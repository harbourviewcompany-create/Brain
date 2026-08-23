from brain.money_spine import (
    DailyRevenueReport,
    ExperimentDecision,
    MoneySpineService,
    RevenueSignal,
)


def test_actionable_signal_packages_offer():
    service = MoneySpineService()
    signal = RevenueSignal(
        raw_signal="Founder publicly asked for urgent vendor recommendations after expansion announcement",
        source_id="founder-community",
        money_lane_id="high_intent_lead_pack",
        evidence_refs=["https://example.test/signal/1"],
        named_buyer="Acme Software",
        decision_maker="VP Operations",
        visible_pain="Urgent vendor search after expansion",
        urgency_reason="Public urgent request",
        payment_path="Sell a sourced high-intent lead pack to agencies serving this market",
        contact_channel="LinkedIn DM",
        commercial_value=0.8,
        confidence=0.75,
        urgency=0.9,
        contactability=0.8,
        execution_difficulty=0.2,
    )

    scored = service.score_signal(signal)
    assert scored.actionable is True
    assert scored.score > 50
    assert scored.next_action

    offer = service.package_offer(signal, scored)
    assert offer.offer_name == "High-Intent Lead Pack"
    assert offer.approval_required is True
    assert "Would you want to see a small sample?" in offer.outreach_script


def test_no_fantasy_filter_rejects_noncommercial_signal():
    service = MoneySpineService()
    signal = RevenueSignal(
        raw_signal="Interesting market article with no buyer, seller, pain, contact, or payment path",
        source_id="news",
        money_lane_id="high_intent_lead_pack",
        evidence_refs=[],
        commercial_value=0.7,
        confidence=0.4,
    )

    scored = service.score_signal(signal)
    assert scored.actionable is False
    assert "no_named_buyer_seller_or_decision_maker" in scored.rejection_reasons
    assert "no_visible_pain_urgency_or_payment_path" in scored.rejection_reasons
    assert "no_contact_channel" in scored.rejection_reasons
    assert "no_evidence_refs" in scored.rejection_reasons


def test_experiment_decision_scale_modify_kill_continue():
    service = MoneySpineService()
    experiment = service.create_experiment("high_intent_lead_pack", price=250)

    scaled = service.evaluate_experiment(
        experiment,
        outreach_sent=12,
        replies=2,
        meetings=1,
        paid_conversions=1,
        revenue=250,
        operator_hours=3,
    )
    assert scaled.decision == ExperimentDecision.SCALE

    modified = service.evaluate_experiment(
        experiment,
        outreach_sent=30,
        replies=3,
        meetings=0,
        paid_conversions=0,
        revenue=0,
        operator_hours=4,
    )
    assert modified.decision == ExperimentDecision.MODIFY

    killed = service.evaluate_experiment(
        experiment,
        outreach_sent=50,
        replies=0,
        meetings=0,
        paid_conversions=0,
        revenue=0,
        operator_hours=5,
    )
    assert killed.decision == ExperimentDecision.KILL

    continued = service.evaluate_experiment(
        experiment,
        outreach_sent=10,
        replies=0,
        meetings=0,
        paid_conversions=0,
        revenue=0,
        operator_hours=1,
    )
    assert continued.decision == ExperimentDecision.CONTINUE


def test_outcome_learning_updates_lane_and_source_scores():
    service = MoneySpineService()
    before = service.lanes["high_intent_lead_pack"].priority_score
    updated = service.apply_outcome_learning(
        "high_intent_lead_pack",
        "founder-community",
        revenue=500,
        reply=True,
        legal_risk=0,
        operator_hours=2,
    )
    assert updated.priority_score > before
    assert service.source_scores["founder-community"] > 0.5

    before_bad = updated.priority_score
    updated_bad = service.apply_outcome_learning(
        "high_intent_lead_pack",
        "founder-community",
        revenue=0,
        reply=False,
        legal_risk=1,
        operator_hours=8,
    )
    assert updated_bad.priority_score < before_bad


def test_daily_revenue_report_enforces_no_passive_research_day():
    incomplete = DailyRevenueReport(
        raw_signals_reviewed=50,
        signals_logged=20,
        qualified_opportunities=10,
        prioritized_opportunities=5,
        direct_revenue_actions=0,
        sellable_assets_created=1,
        lessons_recorded=1,
    )
    assert incomplete.passed is False
    assert "direct_revenue_actions" in incomplete.gaps

    complete = DailyRevenueReport(
        raw_signals_reviewed=50,
        signals_logged=20,
        qualified_opportunities=10,
        prioritized_opportunities=5,
        direct_revenue_actions=3,
        sellable_assets_created=1,
        lessons_recorded=1,
    )
    assert complete.passed is True
    assert complete.gaps == []
