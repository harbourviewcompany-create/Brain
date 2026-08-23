from pathlib import Path

import pytest

from tools.revenue_spine_17_21 import (
    AccessStatus,
    CockpitOutcome,
    ConnectorKind,
    DeterministicModelCortex,
    FixtureConnectorRunner,
    RevenueCockpit,
    SourceConnectorInput,
    first_500_fast_cash,
    generate_opportunity_registry,
    load_go_hold_reconciliation,
    reconcile_go_hold,
    registry_summary,
    validate_registry_row,
)


def test_issue_17_generated_registry_preserves_count_and_first_500():
    rows = generate_opportunity_registry()
    summary = registry_summary(rows)
    fast_cash = first_500_fast_cash(rows)
    assert summary["row_count"] == 10_000
    assert summary["first_500_count"] == 500
    assert len(fast_cash) == 500
    assert fast_cash[0].priority_score >= fast_cash[-1].priority_score


def test_issue_17_registry_rejects_malformed_rows():
    with pytest.raises(ValueError):
        validate_registry_row({"lane_id": "bad"})


def test_issue_18_three_connectors_emit_normalized_candidates():
    runner = FixtureConnectorRunner()
    fixtures = [
        SourceConnectorInput(
            ConnectorKind.MANUAL_TEXT,
            "manual-1",
            "Urgent buyer asking for vendor recommendations",
            "https://example.test/manual",
            metadata={"buyer": "Acme Co", "contact_channel": "email"},
        ),
        SourceConnectorInput(
            ConnectorKind.JOB_BOARD,
            "job-1",
            "Company hiring urgently for multiple implementation roles",
            "https://example.test/job",
            metadata={"company": "BuildCo"},
        ),
        SourceConnectorInput(
            ConnectorKind.PROCUREMENT,
            "rfp-1",
            "RFP deadline for facilities services",
            "https://example.test/rfp",
            metadata={"buyer": "City Buyer"},
        ),
    ]
    candidates = [runner.ingest(item)[0] for item in fixtures]
    assert all(candidate.source_id for candidate in candidates)
    assert all(candidate.evidence_refs for candidate in candidates)
    assert all(candidate.extraction_method == "fixture" for candidate in candidates)
    assert all(candidate.content_hash for candidate in candidates)


def test_issue_18_prohibited_source_blocks_before_ingestion():
    [candidate] = FixtureConnectorRunner().ingest(
        SourceConnectorInput(
            ConnectorKind.AUCTION,
            "auction-1",
            "Auction listing",
            "https://example.test/auction",
            access_status=AccessStatus.PROHIBITED,
        )
    )
    assert candidate.raw_signal.startswith("BLOCKED")
    assert candidate.legal_access_risk == 1
    assert candidate.to_revenue_signal().metadata["access_status"] == "prohibited"


def test_issue_19_model_cortex_blocks_ambiguous_inputs_and_preserves_approval():
    result = DeterministicModelCortex().analyze(
        SourceConnectorInput(
            ConnectorKind.MANUAL_TEXT,
            "manual-ambiguous",
            "Interesting market movement",
            "",
            access_status=AccessStatus.REVIEW_REQUIRED,
        )
    )
    assert result.approval_required is True
    assert "missing_provenance" in result.objections
    assert "access_status_blocks_or_requires_review" in result.objections


def test_issue_19_model_cortex_produces_hypothesis_for_good_fixture():
    result = DeterministicModelCortex().analyze(
        SourceConnectorInput(
            ConnectorKind.MANUAL_TEXT,
            "manual-good",
            "Urgent buyer request before deadline",
            "https://example.test/good",
            metadata={"buyer": "Acme Co", "contact_channel": "email"},
        )
    )
    assert result.objections == []
    assert result.hypotheses[0].evidence_for == ["https://example.test/good"]
    assert result.hypotheses[0].falsification_rule


def test_issue_20_cockpit_requires_approval_and_logs_outcome_learning():
    cockpit = RevenueCockpit()
    signal = FixtureConnectorRunner().ingest(
        SourceConnectorInput(
            ConnectorKind.MANUAL_TEXT,
            "manual-good",
            "Urgent buyer request before deadline",
            "https://example.test/good",
            metadata={"buyer": "Acme Co", "contact_channel": "email"},
        )
    )[0].to_revenue_signal()
    offer_id = cockpit.ingest_signal(signal)
    assert offer_id is not None
    with pytest.raises(PermissionError):
        cockpit.mark_sent(offer_id)
    cockpit.approve_offer(offer_id, "operator")
    cockpit.mark_sent(offer_id)
    action_id = cockpit.actions[offer_id].id
    cockpit.log_outcome(
        offer_id,
        CockpitOutcome(
            action_id,
            "manual-good",
            "high_intent_lead_pack",
            1,
            1,
            1,
            500,
            2,
            False,
            False,
            "Named buyer and urgency converted.",
        ),
    )
    assert cockpit.service.source_scores["manual-good"] > 0.5
    assert cockpit.snapshot()["today_revenue_queue"] == 1


def test_issue_21_go_hold_reconciliation_passes_and_flags_mismatch():
    assert load_go_hold_reconciliation(Path("docs/control/go_hold_issue_reconciliation.json")) == []
    failures = reconcile_go_hold(
        issues=[{"issue_number": 3, "issue_state": "open", "evidence_refs": ["report.json"]}],
        reports=[{"report_id": "GO-HOLD", "verdict": "GO", "issue_numbers": [3], "evidence_refs": ["summary.json"]}],
    )
    assert "open issue #3" in failures[0]
