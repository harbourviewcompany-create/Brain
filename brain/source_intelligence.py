from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceCategory(StrEnum):
    GOVERNMENT_REGISTRY = "government_registry"
    CORPORATE_REGISTRY = "corporate_registry"
    LICENSING_DATABASE = "licensing_database"
    REGULATORY_PORTAL = "regulatory_portal"
    COURT_INSOLVENCY = "court_insolvency"
    PROCUREMENT_PORTAL = "procurement_portal"
    GRANT_SUBSIDY = "grant_subsidy"
    REAL_ESTATE_PROPERTY = "real_estate_property"
    IMPORT_EXPORT_TRADE = "import_export_trade"
    PATENT_TRADEMARK = "patent_trademark"
    SCIENTIFIC_ACADEMIC = "scientific_academic"
    CLINICAL_TRIAL = "clinical_trial"
    JOB_HIRING = "job_hiring"
    COMPANY_CONTROLLED = "company_controlled"
    NEWS_MEDIA = "news_media"
    INDUSTRY_NEWSLETTER = "industry_newsletter"
    SOCIAL_COMMUNITY = "social_community"
    EVENT_CONFERENCE = "event_conference"
    PRODUCT_DIRECTORY = "product_directory"
    REVIEW_PLATFORM = "review_platform"
    GEOSPATIAL_ENVIRONMENTAL = "geospatial_environmental"
    LOGISTICS_SHIPPING = "logistics_shipping"
    ENERGY_GRID = "energy_grid"
    FINANCIAL_FILING = "financial_filing"
    INVESTOR_MA = "investor_ma"
    MARKETPLACE_LISTING = "marketplace_listing"
    MUNICIPAL_RECORD = "municipal_record"
    FOI_OPEN_DATA = "foi_open_data"
    NGO_THINK_TANK = "ngo_think_tank"
    STANDARDS_CERTIFICATION = "standards_certification"
    ENFORCEMENT_RECALL = "enforcement_recall"
    SANCTIONS_WATCHLIST = "sanctions_watchlist"
    WEB_CHANGE_TECH = "web_change_tech"
    ADVERTISING_LIBRARY = "advertising_library"
    PAYMENT_COMMERCIAL_INFRA = "payment_commercial_infra"


class SignalType(StrEnum):
    EXPANSION = "expansion"
    DISTRESS = "distress"
    HIRING = "hiring"
    CAPITAL_RAISE = "capital_raise"
    REGULATORY_CHANGE = "regulatory_change"
    SUPPLY_DEMAND_IMBALANCE = "supply_demand_imbalance"
    ASSET_SALE = "asset_sale"
    BUYER_INTENT = "buyer_intent"
    SELLER_INTENT = "seller_intent"
    LICENSE_MOVEMENT = "license_movement"
    PROCUREMENT = "procurement"
    LITIGATION = "litigation"
    MARKET_ENTRY = "market_entry"
    CLOSURE = "closure"
    CONSOLIDATION = "consolidation"
    PRODUCT_LAUNCH = "product_launch"
    ENFORCEMENT = "enforcement"
    SUPPLY_CHAIN_DISRUPTION = "supply_chain_disruption"
    LOCAL_MARKET_MOVEMENT = "local_market_movement"
    DOMAIN_WEB_CHANGE = "domain_web_change"
    COMMERCIAL_INFRA_CHANGE = "commercial_infra_change"


class AccessMethod(StrEnum):
    API = "api"
    CSV_DOWNLOAD = "csv_download"
    RSS_FEED = "rss_feed"
    HTML_SCRAPE = "html_scrape"
    PDF_EXTRACTION = "pdf_extraction"
    MANUAL_REVIEW = "manual_review"
    EMAIL_CAPTURE = "email_capture"
    BROWSER_AUTOMATION = "browser_automation"
    SEARCH_ALERT = "search_alert"
    THIRD_PARTY_ENRICHMENT = "third_party_enrichment"
    WEB_CHANGE_MONITOR = "web_change_monitor"


class LegalAccessStatus(StrEnum):
    PUBLIC_PERMITTED = "public_permitted"
    OPEN_LICENSE = "open_license"
    PAID_LICENSED = "paid_licensed"
    TERMS_REVIEW_REQUIRED = "terms_review_required"
    PII_SENSITIVE = "pii_sensitive"
    RATE_LIMITED = "rate_limited"
    MANUAL_ONLY = "manual_only"
    PROHIBITED = "prohibited"


class SourceLifecycleStatus(StrEnum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    MONITORED = "monitored"
    DEGRADED = "degraded"
    BROKEN = "broken"
    RETIRED = "retired"
    PROHIBITED = "prohibited"


class OperationalDisposition(StrEnum):
    GO_AUTOMATE_OR_QUEUE = "GO_AUTOMATE_OR_QUEUE"
    GO_MANUAL_ANALYST_REVIEW = "GO_MANUAL_ANALYST_REVIEW"
    WATCH = "WATCH"
    HOLD_TERMS_REVIEW = "HOLD_TERMS_REVIEW"
    HOLD_PII_REVIEW = "HOLD_PII_REVIEW"
    HOLD_PROHIBITED = "HOLD_PROHIBITED"
    REJECT_LOW_VALUE = "REJECT_LOW_VALUE"


class SourceScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_value: int = Field(ge=1, le=5)
    extraction_difficulty: int = Field(ge=1, le=5)
    freshness: int = Field(ge=1, le=5)
    reliability: int = Field(ge=1, le=5)

    @property
    def priority_score(self) -> int:
        return registry_priority_score(
            signal_value=self.signal_value,
            extraction_difficulty=self.extraction_difficulty,
            freshness=self.freshness,
            reliability=self.reliability,
        )


class SourceIntelligenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    source_name: str
    source_category: SourceCategory
    url_or_access_path: str
    jurisdiction_market_coverage: list[str]
    data_contains: list[str]
    signal_types: list[SignalType]
    commercial_value: str
    signal_freshness: str
    update_frequency: str
    access_methods: list[AccessMethod]
    legal_access_status: LegalAccessStatus
    noise_level: Literal["low", "medium", "high"]
    reliability_level: Literal["official_primary", "reputable_structured", "mixed", "noisy", "unreliable"]
    downstream_use_cases: list[str]
    example_intelligence_questions: list[str]
    best_ingestion_method: AccessMethod
    compounding_sources_to_pair: list[str] = Field(default_factory=list)
    score: SourceScore
    priority_score: int | None = None
    lifecycle_status: SourceLifecycleStatus = SourceLifecycleStatus.DISCOVERED
    owner_role: str = "Research Operations / Intelligence Lead"
    review_cadence_days: int = Field(default=90, ge=1)
    provenance_requirements: list[str] = Field(
        default_factory=lambda: [
            "source_id",
            "source_url_or_path",
            "observed_at",
            "retrieved_at",
            "extract_hash_or_snapshot_id",
            "legal_access_status",
        ]
    )
    notes_risks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def materialize_priority_score(self) -> Self:
        expected = self.score.priority_score
        if self.priority_score is None:
            self.priority_score = expected
        if self.priority_score != expected:
            raise ValueError(
                f"priority_score must equal (signal_value*3)+freshness+reliability-extraction_difficulty; expected {expected}"
            )
        return self


class SourceCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str
    detects: str
    source_categories: list[SourceCategory]
    signal_patterns: list[str]
    false_positive_controls: list[str]
    commercial_actions: list[str]


class IngestionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_category: SourceCategory
    permitted_methods: list[AccessMethod]
    default_refresh_cadence: str
    normalization_needs: list[str]
    deduplication_keys: list[str]
    evidence_required: list[str]
    failure_monitoring: list[str]
    compliance_cautions: list[str]


def registry_priority_score(
    *, signal_value: int, extraction_difficulty: int, freshness: int, reliability: int
) -> int:
    """Priority score from the Source Intelligence Registry operating prompt."""
    for name, value in {
        "signal_value": signal_value,
        "extraction_difficulty": extraction_difficulty,
        "freshness": freshness,
        "reliability": reliability,
    }.items():
        if value < 1 or value > 5:
            raise ValueError(f"{name} must be between 1 and 5")
    return (signal_value * 3) + freshness + reliability - extraction_difficulty


def operational_disposition(record: SourceIntelligenceRecord) -> OperationalDisposition:
    if record.legal_access_status == LegalAccessStatus.PROHIBITED:
        return OperationalDisposition.HOLD_PROHIBITED
    if record.legal_access_status == LegalAccessStatus.TERMS_REVIEW_REQUIRED:
        return OperationalDisposition.HOLD_TERMS_REVIEW
    if record.legal_access_status == LegalAccessStatus.PII_SENSITIVE:
        return OperationalDisposition.HOLD_PII_REVIEW
    if record.score.signal_value <= 2 and record.priority_score is not None and record.priority_score < 10:
        return OperationalDisposition.REJECT_LOW_VALUE
    if (
        record.score.signal_value >= 4
        and record.score.extraction_difficulty <= 3
        and record.priority_score is not None
        and record.priority_score >= 16
    ):
        return OperationalDisposition.GO_AUTOMATE_OR_QUEUE
    if record.score.signal_value >= 4:
        return OperationalDisposition.GO_MANUAL_ANALYST_REVIEW
    return OperationalDisposition.WATCH


def rank_sources(records: list[SourceIntelligenceRecord]) -> list[SourceIntelligenceRecord]:
    return sorted(
        records,
        key=lambda record: (
            record.priority_score or record.score.priority_score,
            record.score.signal_value,
            -record.score.extraction_difficulty,
            record.source_name,
        ),
        reverse=True,
    )


def load_registry_fixture(path: str | Path) -> list[SourceIntelligenceRecord]:
    import json

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [SourceIntelligenceRecord.model_validate(item) for item in data["sources"]]


DEFAULT_SOURCE_CLUSTERS: tuple[SourceCluster, ...] = (
    SourceCluster(
        cluster_id="company_distress_detection",
        detects="Financial or operating pressure that may create acquisition, advisory, lending, restructuring, liquidation, or buyer/seller introduction opportunities.",
        source_categories=[
            SourceCategory.COURT_INSOLVENCY,
            SourceCategory.MARKETPLACE_LISTING,
            SourceCategory.JOB_HIRING,
            SourceCategory.NEWS_MEDIA,
            SourceCategory.REGULATORY_PORTAL,
        ],
        signal_patterns=[
            "insolvency or litigation event plus asset-sale listing",
            "layoff or closure signal plus equipment or property disposition",
            "regulatory enforcement plus supplier/customer disruption",
        ],
        false_positive_controls=[
            "require timestamped primary evidence before action",
            "separate promotional news from legal or operating evidence",
            "downgrade stale filings unless corroborated by a recent event",
        ],
        commercial_actions=[
            "prepare distressed-asset brief",
            "identify likely buyers or service providers",
            "route to fee-protected outreach approval",
        ],
    ),
    SourceCluster(
        cluster_id="hiring_expansion_market_entry",
        detects="Expansion, new-market entry, capability buildout, and buyer or partner intent.",
        source_categories=[
            SourceCategory.JOB_HIRING,
            SourceCategory.LICENSING_DATABASE,
            SourceCategory.MUNICIPAL_RECORD,
            SourceCategory.COMPANY_CONTROLLED,
            SourceCategory.EVENT_CONFERENCE,
        ],
        signal_patterns=[
            "new license plus local hiring plus facility permit",
            "country manager hiring plus distributor search language",
            "conference exhibitor activity plus product-launch announcement",
        ],
        false_positive_controls=[
            "do not treat one generic job post as expansion",
            "verify location and role seniority",
            "require at least one corroborating non-company-controlled source for high-consequence action",
        ],
        commercial_actions=[
            "build market-entry memo",
            "generate buyer, distributor, or partner list",
            "create monitoring queue or paid brief candidate",
        ],
    ),
    SourceCluster(
        cluster_id="regulatory_supply_gap",
        detects="Regulatory shifts, shortages, compliance changes, and supply-demand gaps that can create advisory, sourcing, licensing, or distribution opportunities.",
        source_categories=[
            SourceCategory.REGULATORY_PORTAL,
            SourceCategory.ENFORCEMENT_RECALL,
            SourceCategory.IMPORT_EXPORT_TRADE,
            SourceCategory.LOGISTICS_SHIPPING,
            SourceCategory.FOI_OPEN_DATA,
        ],
        signal_patterns=[
            "new regulation plus importer license movement",
            "recall or enforcement action plus substitute supplier availability",
            "trade-flow change plus local shortage or procurement demand",
        ],
        false_positive_controls=[
            "distinguish proposed rules from adopted rules",
            "record jurisdiction and effective date",
            "require legal review before regulated commercial action",
        ],
        commercial_actions=[
            "prepare compliance or supply-gap alert",
            "source replacement suppliers",
            "route regulated action to HOLD until approved",
        ],
    ),
)


DEFAULT_INGESTION_POLICIES: tuple[IngestionPolicy, ...] = (
    IngestionPolicy(
        source_category=SourceCategory.CORPORATE_REGISTRY,
        permitted_methods=[AccessMethod.API, AccessMethod.CSV_DOWNLOAD, AccessMethod.HTML_SCRAPE, AccessMethod.MANUAL_REVIEW],
        default_refresh_cadence="weekly for watched entities; monthly for broad coverage",
        normalization_needs=["entity legal name", "registration number", "jurisdiction", "address", "officers", "status"],
        deduplication_keys=["jurisdiction", "registration_number", "legal_name"],
        evidence_required=["source snapshot", "retrieval timestamp", "entity identifier", "jurisdiction"],
        failure_monitoring=["schema drift", "rate limit", "captcha or access change", "stale records"],
        compliance_cautions=["respect terms of use", "preserve official-source provenance", "flag personal data fields"],
    ),
    IngestionPolicy(
        source_category=SourceCategory.JOB_HIRING,
        permitted_methods=[AccessMethod.API, AccessMethod.HTML_SCRAPE, AccessMethod.SEARCH_ALERT, AccessMethod.THIRD_PARTY_ENRICHMENT],
        default_refresh_cadence="daily for tracked companies; weekly for discovery scans",
        normalization_needs=["company", "role", "location", "seniority", "posted_at", "closed_at"],
        deduplication_keys=["company", "role", "location", "posted_at"],
        evidence_required=["posting URL", "posting text hash", "observed_at", "role classification"],
        failure_monitoring=["duplicate syndicated postings", "expired roles", "promoted listings", "location ambiguity"],
        compliance_cautions=["avoid collecting applicant personal data", "separate role signal from inferred business claim"],
    ),
    IngestionPolicy(
        source_category=SourceCategory.REGULATORY_PORTAL,
        permitted_methods=[AccessMethod.API, AccessMethod.RSS_FEED, AccessMethod.PDF_EXTRACTION, AccessMethod.MANUAL_REVIEW],
        default_refresh_cadence="daily to weekly depending on regulator cadence",
        normalization_needs=["regulator", "jurisdiction", "effective date", "rule status", "affected sector"],
        deduplication_keys=["regulator", "document_id", "publication_date"],
        evidence_required=["official document link", "effective date", "rule status", "retrieval timestamp"],
        failure_monitoring=["PDF layout change", "consultation vs adopted rule confusion", "translation ambiguity"],
        compliance_cautions=["legal interpretation is HOLD until reviewed", "preserve exact source document references"],
    ),
)
