from pathlib import Path

import pytest

from brain.source_intelligence import (
    DEFAULT_INGESTION_POLICIES,
    DEFAULT_SOURCE_CLUSTERS,
    LegalAccessStatus,
    OperationalDisposition,
    SourceCategory,
    SourceCluster,
    SourceIntelligenceRecord,
    SourceLifecycleStatus,
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
            "score": {
                "signal_value": 5,
                "extraction_difficulty": 2,
                "freshness": 4,
                "reliability": 5,
            },
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


def test_manual_only_and_prohibited_lifecycle_never_auto_route() -> None:
    base = load_registry_fixture(FIXTURE)[0]
    manual_record = base.model_copy(update={"legal_access_status": LegalAccessStatus.MANUAL_ONLY})
    lifecycle_prohibited_record = base.model_copy(
        update={"lifecycle_status": SourceLifecycleStatus.PROHIBITED}
    )

    assert operational_disposition(manual_record) == OperationalDisposition.GO_MANUAL_ANALYST_REVIEW
    assert operational_disposition(lifecycle_prohibited_record) == OperationalDisposition.HOLD_PROHIBITED


def test_paid_licensed_source_requires_license_review_before_automation() -> None:
    base = load_registry_fixture(FIXTURE)[0]
    paid_record = base.model_copy(update={"legal_access_status": LegalAccessStatus.PAID_LICENSED})

    assert paid_record.priority_score >= 16
    assert operational_disposition(paid_record) == OperationalDisposition.HOLD_LICENSE_REVIEW


def test_missing_mandatory_provenance_is_rejected() -> None:
    payload = load_registry_fixture(FIXTURE)[0].model_dump(mode="json")
    payload.pop("declared_priority_score", None)
    payload["provenance_requirements"] = []

    with pytest.raises(ValueError):
        SourceIntelligenceRecord.model_validate(payload)


def test_active_record_requires_operational_update_frequency() -> None:
    payload = load_registry_fixture(FIXTURE)[0].model_dump(mode="json")
    payload.pop("declared_priority_score", None)
    payload["lifecycle_status"] = "active"
    payload["update_frequency"] = " "

    with pytest.raises(ValueError, match="update_frequency"):
        SourceIntelligenceRecord.model_validate(payload)


def test_priority_score_is_derived_and_score_is_immutable() -> None:
    record = load_registry_fixture(FIXTURE)[0]
    assert record.priority_score == 23

    with pytest.raises(Exception):
        record.priority_score = 1  # type: ignore[misc]

    with pytest.raises(Exception):
        record.score.signal_value = 1


def test_registry_timestamps_are_timezone_aware() -> None:
    record = SourceIntelligenceRecord.model_validate(
        {
            "source_name": "Timezone registry class",
            "source_category": "corporate_registry",
            "url_or_access_path": "official registry",
            "jurisdiction_market_coverage": ["global_by_jurisdiction"],
            "data_contains": ["legal entity status"],
            "signal_types": ["market_entry"],
            "commercial_value": "entity verification",
            "signal_freshness": "registry-dependent",
            "update_frequency": "daily to monthly",
            "access_methods": ["api"],
            "legal_access_status": "public_permitted",
            "noise_level": "medium",
            "reliability_level": "official_primary",
            "downstream_use_cases": ["counterparty verification"],
            "example_intelligence_questions": ["Which entities were newly formed?"],
            "best_ingestion_method": "api",
            "score": {
                "signal_value": 5,
                "extraction_difficulty": 2,
                "freshness": 4,
                "reliability": 5,
            },
        }
    )

    assert record.created_at.tzinfo is not None
    assert record.updated_at.tzinfo is not None


def test_source_cluster_requires_false_positive_controls() -> None:
    with pytest.raises(ValueError):
        SourceCluster(
            cluster_id="bad_cluster",
            detects="unsupported promotion",
            source_categories=[SourceCategory.NEWS_MEDIA],
            signal_patterns=["press release only"],
            false_positive_controls=[],
            commercial_actions=["act"],
        )
