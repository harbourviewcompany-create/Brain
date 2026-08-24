from pathlib import Path

import pytest

from brain.source_intelligence import (
    DEFAULT_INGESTION_POLICIES,
    DEFAULT_SOURCE_CLUSTERS,
    LegalAccessStatus,
    OperationalDisposition,
    SourceIntelligenceRecord,
    SourceScore,
    load_registry_fixture,
    operational_disposition,
    rank_sources,
    registry_priority_score,
)


FIXTURE = Path("tests/fixtures/brain/source_intelligence_registry.json")


def test_registry_priority_score_formula() -> None:
    assert registry_priority_score(
        signal_value=5,
        extraction_difficulty=2,
        freshness=5,
        reliability=5,
    ) == 23

    with pytest.raises(ValueError):
        registry_priority_score(
            signal_value=6,
            extraction_difficulty=2,
            freshness=5,
            reliability=5,
        )


def test_source_record_materializes_and_validates_priority_score() -> None:
    record = SourceIntelligenceRecord.model_validate(
        {
            "source_name": "Jurisdiction corporate registry class",
            "source_category": "corporate_registry",
            "url_or_access_path": "jurisdiction-specific official registry or API",
            "jurisdiction_market_coverage": ["global_by_jurisdiction"],
            "data_contains": ["legal entity status", "officers", "registered address"],
            "signal_types": ["market_entry", "closure", "consolidation"],
            "commercial_value": "entity verification and movement detection",
            "signal_freshness": "registry-dependent",
            "update_frequency": "daily to monthly",
            "access_methods": ["api", "csv_download", "manual_review"],
            "legal_access_status": "public_permitted",
            "noise_level": "medium",
            "reliability_level": "official_primary",
            "downstream_use_cases": ["counterparty verification", "market movement monitoring"],
            "example_intelligence_questions": ["Which entities were newly formed in this sector?"],
            "best_ingestion_method": "api",
            "score": {"signal_value": 5, "extraction_difficulty": 2, "freshness": 4, "reliability": 5},
        }
    )

    assert record.priority_score == 22
    assert operational_disposition(record) == OperationalDisposition.GO_AUTOMATE_OR_QUEUE

    payload = record.model_dump(mode="json")
    payload["priority_score"] = 1
    with pytest.raises(ValueError):
        SourceIntelligenceRecord.model_validate(payload)


def test_legal_access_status_forces_hold() -> None:
    base = load_registry_fixture(FIXTURE)[0]
    pii_record = base.model_copy(update={"legal_access_status": LegalAccessStatus.PII_SENSITIVE})
    prohibited_record = base.model_copy(update={"legal_access_status": LegalAccessStatus.PROHIBITED})

    assert operational_disposition(pii_record) == OperationalDisposition.HOLD_PII_REVIEW
    assert operational_disposition(prohibited_record) == OperationalDisposition.HOLD_PROHIBITED


def test_fixture_registry_ranks_sources_by_operational_priority() -> None:
    records = load_registry_fixture(FIXTURE)
    ranked = rank_sources(records)

    assert records
    assert ranked[0].priority_score >= ranked[-1].priority_score
    assert ranked[0].score == SourceScore(
        signal_value=5,
        extraction_difficulty=2,
        freshness=5,
        reliability=5,
    )
    assert operational_disposition(ranked[0]) == OperationalDisposition.GO_AUTOMATE_OR_QUEUE


def test_default_clusters_and_ingestion_policies_are_operator_grade() -> None:
    assert len(DEFAULT_SOURCE_CLUSTERS) >= 3
    assert len(DEFAULT_INGESTION_POLICIES) >= 3

    for cluster in DEFAULT_SOURCE_CLUSTERS:
        assert cluster.signal_patterns
        assert cluster.false_positive_controls
        assert cluster.commercial_actions

    for policy in DEFAULT_INGESTION_POLICIES:
        assert policy.permitted_methods
        assert policy.evidence_required
        assert policy.compliance_cautions
