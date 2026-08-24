from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self
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
    HOLD_LICENSE_REVIEW = "HOLD_LICENSE_REVIEW"
    HOLD_TERMS_REVIEW = "HOLD_TERMS_REVIEW"
    HOLD_PII_REVIEW = "HOLD_PII_REVIEW"
    HOLD_PROHIBITED = "HOLD_PROHIBITED"
    REJECT_LOW_VALUE = "REJECT_LOW_VALUE"


class SourceScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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


MANDATORY_PROVENANCE_REQUIREMENTS = frozenset(
    {
        "source_id",
        "source_url_or_path",
        "observed_at",
        "retrieved_at",
        "extract_hash_or_snapshot_id",
        "legal_access_status",
    }
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class SourceIntelligenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    source_name: str
    source_category: SourceCategory
    url_or_access_path: str
    jurisdiction_market_coverage: list[str] = Field(min_length=1)
    data_contains: list[str] = Field(min_length=1)
    signal_types: list[SignalType] = Field(min_length=1)
    commercial_value: str
    signal_freshness: str
    update_frequency: str
    access_methods: list[AccessMethod] = Field(min_length=1)
    legal_access_status: LegalAccessStatus
    noise_level: Literal["low", "medium", "high"]
    reliability_level: Literal[
        "official_primary", "reputable_structured", "mixed", "noisy", "unreliable"
    ]
    downstream_use_cases: list[str] = Field(min_length=1)
    example_intelligence_questions: list[str] = Field(min_length=1)
    best_ingestion_method: AccessMethod
    compounding_sources_to_pair: list[str] = Field(default_factory=list)
    score: SourceScore
    declared_priority_score: int | None = Field(
        default=None,
        validation_alias="priority_score",
        serialization_alias="declared_priority_score",
    )
    lifecycle_status: SourceLifecycleStatus = SourceLifecycleStatus.DISCOVERED
    owner_role: str = "Research Operations / Intelligence Lead"
    review_cadence_days: int = Field(default=90, ge=1)
    provenance_requirements: list[str] = Field(
        default_factory=lambda: sorted(MANDATORY_PROVENANCE_REQUIREMENTS)
    )
    notes_risks: list[str] = Field(default_factory=list)

    @property
    def priority_score(self) -> int:
        return self.score.priority_score

    @model_validator(mode="after")
    def validate_priority_and_provenance(self) -> Self:
        expected = self.score.priority_score
        if self.declared_priority_score is not None and self.declared_priority_score != expected:
            raise ValueError(
                "priority_score must equal "
                "(signal_value*3)+freshness+reliability-extraction_difficulty; "
                f"expected {expected}"
            )
        missing = MANDATORY_PROVENANCE_REQUIREMENTS - set(self.provenance_requirements)
        if missing:
            raise ValueError(f"provenance_requirements missing mandatory keys: {sorted(missing)}")
        if self.lifecycle_status == SourceLifecycleStatus.ACTIVE:
            missing_active_fields = []
            if not self.jurisdiction_market_coverage:
                missing_active_fields.append("jurisdiction_market_coverage")
            if not self.downstream_use_cases:
                missing_active_fields.append("downstream_use_cases")
            if not self.provenance_requirements:
                missing_active_fields.append("provenance_requirements")
            if not self.update_frequency.strip():
                missing_active_fields.append("update_frequency")
            if missing_active_fields:
                raise ValueError(
                    "active source records require operational metadata: "
                    f"{sorted(missing_active_fields)}"
                )
        return self


class SourceCluster(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cluster_id: str
    detects: str
    source_categories: list[SourceCategory] = Field(min_length=1)
    signal_patterns: list[str] = Field(min_length=1)
    false_positive_controls: list[str] = Field(min_length=1)
    commercial_actions: list[str] = Field(min_length=1)


class IngestionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_category: SourceCategory
    permitted_methods: list[AccessMethod] = Field(min_length=1)
    default_refresh_cadence: str
    normalization_needs: list[str] = Field(min_length=1)
    deduplication_keys: list[str] = Field(min_length=1)
    evidence_required: list[str] = Field(min_length=1)
    failure_monitoring: list[str] = Field(min_length=1)
    compliance_cautions: list[str] = Field(min_length=1)


def registry_priority_score(
    *, signal_value: int, extraction_difficulty: int, freshness: int, reliability: int
) -> int:
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
    if (
        record.legal_access_status == LegalAccessStatus.PROHIBITED
        or record.lifecycle_status == SourceLifecycleStatus.PROHIBITED
    ):
        return OperationalDisposition.HOLD_PROHIBITED
    if record.legal_access_status == LegalAccessStatus.TERMS_REVIEW_REQUIRED:
        return OperationalDisposition.HOLD_TERMS_REVIEW
    if record.legal_access_status == LegalAccessStatus.PII_SENSITIVE:
        return OperationalDisposition.HOLD_PII_REVIEW
    if record.legal_access_status == LegalAccessStatus.PAID_LICENSED:
        return OperationalDisposition.HOLD_LICENSE_REVIEW
    if record.legal_access_status == LegalAccessStatus.MANUAL_ONLY:
        if record.score.signal_value >= 4:
            return OperationalDisposition.GO_MANUAL_ANALYST_REVIEW
        return OperationalDisposition.WATCH
    if record.score.signal_value <= 2 and record.priority_score < 10:
        return OperationalDisposition.REJECT_LOW_VALUE
    if (
        record.score.signal_value >= 4
        and record.score.extraction_difficulty <= 3
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
            record.priority_score,
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
        detects=(
            "Financial or operating pressure that may create acquisition, advisory, lending, "
            "restructuring, liquidation, or buyer/seller introduction opportunities."
        ),
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
        detects=(
            "Regulatory shifts, shortages, compliance changes, and supply-demand gaps that can "
            "create advisory, sourcing, licensing, or distribution opportunities."
        ),
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
        permitted_methods=[
            AccessMethod.API,
            AccessMethod.CSV_DOWNLOAD,
            AccessMethod.HTML_SCRAPE,
            AccessMethod.MANUAL_REVIEW,
        ],
        default_refresh_cadence="weekly for watched entities; monthly for broad coverage",
        normalization_needs=[
            "entity legal name",
            "registration number",
            "jurisdiction",
            "address",
            "officers",
            "status",
        ],
        deduplication_keys=["jurisdiction", "registration_number", "legal_name"],
        evidence_required=["source snapshot", "retrieval timestamp", "entity identifier", "jurisdiction"],
        failure_monitoring=["schema drift", "rate limit", "captcha or access change", "stale records"],
        compliance_cautions=[
            "respect terms of use",
            "preserve official-source provenance",
            "flag personal data fields",
        ],
    ),
    IngestionPolicy(
        source_category=SourceCategory.JOB_HIRING,
        permitted_methods=[
            AccessMethod.API,
            AccessMethod.HTML_SCRAPE,
            AccessMethod.SEARCH_ALERT,
            AccessMethod.THIRD_PARTY_ENRICHMENT,
        ],
        default_refresh_cadence="daily for tracked companies; weekly for discovery scans",
        normalization_needs=["company", "role", "location", "seniority", "posted_at", "closed_at"],
        deduplication_keys=["company", "role", "location", "posted_at"],
        evidence_required=["posting URL", "posting text hash", "observed_at", "role classification"],
        failure_monitoring=[
            "duplicate syndicated postings",
            "expired roles",
            "promoted listings",
            "location ambiguity",
        ],
        compliance_cautions=[
            "avoid collecting applicant personal data",
            "separate role signal from inferred business claim",
        ],
    ),
    IngestionPolicy(
        source_category=SourceCategory.REGULATORY_PORTAL,
        permitted_methods=[
            AccessMethod.API,
            AccessMethod.RSS_FEED,
            AccessMethod.PDF_EXTRACTION,
            AccessMethod.MANUAL_REVIEW,
        ],
        default_refresh_cadence="daily to weekly depending on regulator cadence",
        normalization_needs=["regulator", "jurisdiction", "effective date", "rule status", "affected sector"],
        deduplication_keys=["regulator", "document_id", "publication_date"],
        evidence_required=["official document link", "effective date", "rule status", "retrieval timestamp"],
        failure_monitoring=["PDF layout change", "consultation vs adopted rule confusion", "translation ambiguity"],
        compliance_cautions=[
            "legal interpretation is HOLD until reviewed",
            "preserve exact source document references",
        ],
    ),
)


class IngestionRunStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class SourceObservationStatus(StrEnum):
    RECORDED = "recorded"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class SignalReviewStatus(StrEnum):
    INBOX = "inbox"
    NEEDS_EVIDENCE = "needs_evidence"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROMOTED_TO_OPPORTUNITY = "promoted_to_opportunity"
    HOLD = "hold"


class SourceHealthStatus(StrEnum):
    HEALTHY = "healthy"
    STALE = "stale"
    DEGRADED = "degraded"
    BROKEN = "broken"
    RETIRED = "retired"


class SourceRegistryRuntimeError(ValueError):
    pass


class SourceRegistryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    source_id: UUID | None = None
    related_object_id: UUID | None = None
    event_type: str
    occurred_at: datetime = Field(default_factory=utcnow)
    actor: str = "system"
    detail: str


class IngestionRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    access_method: AccessMethod
    status: IngestionRunStatus = IngestionRunStatus.STARTED
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    observations_created: int = Field(default=0, ge=0)
    error_message: str | None = None


class SourceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    ingestion_run_id: UUID | None = None
    source_url_or_path: str
    observed_at: datetime = Field(default_factory=utcnow)
    retrieved_at: datetime = Field(default_factory=utcnow)
    extract_hash_or_snapshot_id: str
    legal_access_status: LegalAccessStatus
    signal_types: list[SignalType] = Field(min_length=1)
    raw_summary: str
    normalized_entities: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    status: SourceObservationStatus = SourceObservationStatus.RECORDED

    @model_validator(mode="after")
    def validate_observation_trace(self) -> Self:
        if not self.source_url_or_path.strip():
            raise ValueError("source_url_or_path is mandatory observation provenance")
        if not self.extract_hash_or_snapshot_id.strip():
            raise ValueError("extract_hash_or_snapshot_id is mandatory observation provenance")
        if not self.raw_summary.strip():
            raise ValueError("raw_summary is required before signal intake")
        return self


class SignalInboxItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_id: UUID = Field(default_factory=uuid4)
    observation_id: UUID
    source_id: UUID
    title: str
    signal_types: list[SignalType] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    review_status: SignalReviewStatus = SignalReviewStatus.INBOX
    routed_at: datetime = Field(default_factory=utcnow)
    downstream_use_cases: list[str] = Field(default_factory=list)
    action_suggestions: list[str] = Field(default_factory=list)
    reviewer: str | None = None
    review_note: str | None = None


class SourceHealthCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    health_check_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    checked_at: datetime = Field(default_factory=utcnow)
    status: SourceHealthStatus
    message: str
    consecutive_failures: int = Field(default=0, ge=0)
    next_review_at: datetime | None = None


class SourceRegistrySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utcnow)
    sources: list[SourceIntelligenceRecord] = Field(default_factory=list)
    ingestion_runs: list[IngestionRun] = Field(default_factory=list)
    observations: list[SourceObservation] = Field(default_factory=list)
    signal_inbox: list[SignalInboxItem] = Field(default_factory=list)
    health_checks: list[SourceHealthCheck] = Field(default_factory=list)
    events: list[SourceRegistryEvent] = Field(default_factory=list)


class PersistentSourceRegistryRuntime:
    """Deterministic MOD-017 persistence boundary for source registry and signal intake.

    This runtime is intentionally connector-free. It validates lifecycle, provenance,
    duplicate observations, signal intake, source health and replay snapshots without
    performing live scraping, API calls, browser automation or external commercial action.
    """

    def __init__(self, snapshot: SourceRegistrySnapshot | None = None) -> None:
        self.sources: dict[UUID, SourceIntelligenceRecord] = {}
        self.ingestion_runs: dict[UUID, IngestionRun] = {}
        self.observations: dict[UUID, SourceObservation] = {}
        self.signal_inbox: dict[UUID, SignalInboxItem] = {}
        self.health_checks: dict[UUID, SourceHealthCheck] = {}
        self.events: list[SourceRegistryEvent] = []
        self._observation_hash_index: dict[tuple[UUID, str], UUID] = {}
        self._signal_by_observation: dict[UUID, UUID] = {}
        if snapshot is not None:
            self.load_snapshot(snapshot)

    def emit_event(
        self,
        event_type: str,
        detail: str,
        *,
        source_id: UUID | None = None,
        related_object_id: UUID | None = None,
        actor: str = "system",
    ) -> SourceRegistryEvent:
        event = SourceRegistryEvent(
            source_id=source_id,
            related_object_id=related_object_id,
            event_type=event_type,
            actor=actor,
            detail=detail,
        )
        self.events.append(event)
        return event

    def register_source(
        self, record: SourceIntelligenceRecord, *, actor: str = "system"
    ) -> SourceIntelligenceRecord:
        if record.id in self.sources:
            raise SourceRegistryRuntimeError(f"source already registered: {record.id}")
        self.sources[record.id] = record
        self.emit_event(
            "SOURCE_REGISTERED",
            f"Registered source {record.source_name}",
            source_id=record.id,
            actor=actor,
        )
        return record

    def update_source_lifecycle(
        self,
        source_id: UUID,
        lifecycle_status: SourceLifecycleStatus,
        *,
        actor: str = "system",
    ) -> SourceIntelligenceRecord:
        source = self.require_source(source_id)
        updated = source.model_copy(update={"lifecycle_status": lifecycle_status, "updated_at": utcnow()})
        disposition = operational_disposition(updated)
        if disposition in {
            OperationalDisposition.HOLD_PROHIBITED,
            OperationalDisposition.HOLD_TERMS_REVIEW,
            OperationalDisposition.HOLD_PII_REVIEW,
            OperationalDisposition.HOLD_LICENSE_REVIEW,
        } and lifecycle_status in {SourceLifecycleStatus.ACTIVE, SourceLifecycleStatus.MONITORED}:
            raise SourceRegistryRuntimeError(
                f"cannot activate source with disposition {disposition}"
            )
        self.sources[source_id] = updated
        self.emit_event(
            "SOURCE_LIFECYCLE_UPDATED",
            f"Source lifecycle set to {lifecycle_status}",
            source_id=source_id,
            actor=actor,
        )
        return updated

    def start_ingestion_run(
        self, source_id: UUID, access_method: AccessMethod, *, actor: str = "system"
    ) -> IngestionRun:
        source = self.require_source(source_id)
        disposition = operational_disposition(source)
        if disposition in {
            OperationalDisposition.HOLD_PROHIBITED,
            OperationalDisposition.HOLD_TERMS_REVIEW,
            OperationalDisposition.HOLD_PII_REVIEW,
            OperationalDisposition.HOLD_LICENSE_REVIEW,
            OperationalDisposition.REJECT_LOW_VALUE,
        }:
            raise SourceRegistryRuntimeError(f"source is not eligible for ingestion: {disposition}")
        if source.legal_access_status == LegalAccessStatus.MANUAL_ONLY and access_method != AccessMethod.MANUAL_REVIEW:
            raise SourceRegistryRuntimeError("manual_only sources cannot start automated ingestion")
        if access_method not in source.access_methods:
            raise SourceRegistryRuntimeError(f"access method {access_method} is not registered for source")
        run = IngestionRun(source_id=source_id, access_method=access_method)
        self.ingestion_runs[run.run_id] = run
        self.emit_event(
            "INGESTION_RUN_STARTED",
            f"Started ingestion run with {access_method}",
            source_id=source_id,
            related_object_id=run.run_id,
            actor=actor,
        )
        return run

    def record_observation(
        self,
        source_id: UUID,
        *,
        raw_summary: str,
        extract_hash_or_snapshot_id: str,
        evidence_refs: list[str],
        ingestion_run_id: UUID | None = None,
        signal_types: list[SignalType] | None = None,
        normalized_entities: list[str] | None = None,
        confidence: float = 0.5,
        actor: str = "system",
    ) -> SourceObservation:
        source = self.require_source(source_id)
        if ingestion_run_id is not None and ingestion_run_id not in self.ingestion_runs:
            raise SourceRegistryRuntimeError(f"unknown ingestion run: {ingestion_run_id}")
        key = (source_id, extract_hash_or_snapshot_id)
        if key in self._observation_hash_index:
            observation = self.observations[self._observation_hash_index[key]]
            self.emit_event(
                "SOURCE_OBSERVATION_DEDUPED",
                f"Duplicate observation suppressed for hash {extract_hash_or_snapshot_id}",
                source_id=source_id,
                related_object_id=observation.observation_id,
                actor=actor,
            )
            return observation
        observation = SourceObservation(
            source_id=source_id,
            ingestion_run_id=ingestion_run_id,
            source_url_or_path=source.url_or_access_path,
            extract_hash_or_snapshot_id=extract_hash_or_snapshot_id,
            legal_access_status=source.legal_access_status,
            signal_types=signal_types or source.signal_types,
            raw_summary=raw_summary,
            normalized_entities=normalized_entities or [],
            evidence_refs=evidence_refs,
            confidence=confidence,
        )
        self.observations[observation.observation_id] = observation
        self._observation_hash_index[key] = observation.observation_id
        if ingestion_run_id is not None:
            run = self.ingestion_runs[ingestion_run_id]
            self.ingestion_runs[ingestion_run_id] = run.model_copy(
                update={"observations_created": run.observations_created + 1}
            )
        self.emit_event(
            "SOURCE_OBSERVATION_RECORDED",
            "Recorded source observation with mandatory provenance",
            source_id=source_id,
            related_object_id=observation.observation_id,
            actor=actor,
        )
        return observation

    def complete_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: IngestionRunStatus = IngestionRunStatus.COMPLETED,
        error_message: str | None = None,
        actor: str = "system",
    ) -> IngestionRun:
        if run_id not in self.ingestion_runs:
            raise SourceRegistryRuntimeError(f"unknown ingestion run: {run_id}")
        run = self.ingestion_runs[run_id]
        completed = run.model_copy(
            update={"status": status, "completed_at": utcnow(), "error_message": error_message}
        )
        self.ingestion_runs[run_id] = completed
        self.emit_event(
            "INGESTION_RUN_COMPLETED",
            f"Ingestion run completed with status {status}",
            source_id=completed.source_id,
            related_object_id=run_id,
            actor=actor,
        )
        return completed

    def create_signal_from_observation(
        self, observation_id: UUID, *, actor: str = "system"
    ) -> SignalInboxItem:
        if observation_id not in self.observations:
            raise SourceRegistryRuntimeError(f"unknown observation: {observation_id}")
        if observation_id in self._signal_by_observation:
            return self.signal_inbox[self._signal_by_observation[observation_id]]
        observation = self.observations[observation_id]
        source = self.require_source(observation.source_id)
        status = (
            SignalReviewStatus.INBOX
            if observation.confidence >= 0.55 and observation.evidence_refs
            else SignalReviewStatus.NEEDS_EVIDENCE
        )
        signal = SignalInboxItem(
            observation_id=observation_id,
            source_id=observation.source_id,
            title=f"{source.source_name}: {observation.raw_summary[:96]}",
            signal_types=observation.signal_types,
            evidence_refs=observation.evidence_refs,
            confidence=observation.confidence,
            review_status=status,
            downstream_use_cases=source.downstream_use_cases,
            action_suggestions=[
                "analyst_review",
                "evidence_viewer",
                "opportunity_board_candidate",
            ],
        )
        self.signal_inbox[signal.signal_id] = signal
        self._signal_by_observation[observation_id] = signal.signal_id
        self.emit_event(
            "SIGNAL_INBOX_ITEM_CREATED",
            f"Signal routed to {status}",
            source_id=source.id,
            related_object_id=signal.signal_id,
            actor=actor,
        )
        return signal

    def review_signal(
        self,
        signal_id: UUID,
        review_status: SignalReviewStatus,
        *,
        reviewer: str,
        review_note: str,
    ) -> SignalInboxItem:
        if signal_id not in self.signal_inbox:
            raise SourceRegistryRuntimeError(f"unknown signal: {signal_id}")
        if review_status not in {
            SignalReviewStatus.APPROVED,
            SignalReviewStatus.REJECTED,
            SignalReviewStatus.HOLD,
            SignalReviewStatus.PROMOTED_TO_OPPORTUNITY,
        }:
            raise SourceRegistryRuntimeError("review_signal requires a terminal or operator HOLD status")
        signal = self.signal_inbox[signal_id]
        updated = signal.model_copy(
            update={"review_status": review_status, "reviewer": reviewer, "review_note": review_note}
        )
        self.signal_inbox[signal_id] = updated
        self.emit_event(
            "SIGNAL_REVIEW_RECORDED",
            f"Signal reviewed as {review_status}: {review_note}",
            source_id=updated.source_id,
            related_object_id=signal_id,
            actor=reviewer,
        )
        return updated

    def record_health_check(
        self,
        source_id: UUID,
        status: SourceHealthStatus,
        message: str,
        *,
        consecutive_failures: int = 0,
        next_review_at: datetime | None = None,
        actor: str = "system",
    ) -> SourceHealthCheck:
        self.require_source(source_id)
        health = SourceHealthCheck(
            source_id=source_id,
            status=status,
            message=message,
            consecutive_failures=consecutive_failures,
            next_review_at=next_review_at,
        )
        self.health_checks[health.health_check_id] = health
        if status == SourceHealthStatus.BROKEN:
            self.sources[source_id] = self.sources[source_id].model_copy(
                update={"lifecycle_status": SourceLifecycleStatus.BROKEN, "updated_at": utcnow()}
            )
        elif status == SourceHealthStatus.DEGRADED:
            self.sources[source_id] = self.sources[source_id].model_copy(
                update={"lifecycle_status": SourceLifecycleStatus.DEGRADED, "updated_at": utcnow()}
            )
        self.emit_event(
            "SOURCE_HEALTH_CHECK_RECORDED",
            f"Source health check recorded as {status}: {message}",
            source_id=source_id,
            related_object_id=health.health_check_id,
            actor=actor,
        )
        return health

    def dashboard(self) -> dict[str, int]:
        return {
            "sources": len(self.sources),
            "ingestion_runs": len(self.ingestion_runs),
            "observations": len(self.observations),
            "signals": len(self.signal_inbox),
            "events": len(self.events),
            "health_checks": len(self.health_checks),
            "open_signals": sum(
                1
                for signal in self.signal_inbox.values()
                if signal.review_status in {SignalReviewStatus.INBOX, SignalReviewStatus.NEEDS_EVIDENCE}
            ),
        }

    def list_signal_inbox(
        self, review_status: SignalReviewStatus | None = None
    ) -> list[SignalInboxItem]:
        signals = list(self.signal_inbox.values())
        if review_status is None:
            return signals
        return [signal for signal in signals if signal.review_status == review_status]

    def source_events(self, source_id: UUID) -> list[SourceRegistryEvent]:
        self.require_source(source_id)
        return [event for event in self.events if event.source_id == source_id]

    def snapshot(self) -> SourceRegistrySnapshot:
        return SourceRegistrySnapshot(
            sources=list(self.sources.values()),
            ingestion_runs=list(self.ingestion_runs.values()),
            observations=list(self.observations.values()),
            signal_inbox=list(self.signal_inbox.values()),
            health_checks=list(self.health_checks.values()),
            events=self.events,
        )

    def load_snapshot(self, snapshot: SourceRegistrySnapshot) -> None:
        self.sources = {source.id: source for source in snapshot.sources}
        self.ingestion_runs = {run.run_id: run for run in snapshot.ingestion_runs}
        self.observations = {observation.observation_id: observation for observation in snapshot.observations}
        self.signal_inbox = {signal.signal_id: signal for signal in snapshot.signal_inbox}
        self.health_checks = {health.health_check_id: health for health in snapshot.health_checks}
        self.events = list(snapshot.events)
        self._observation_hash_index = {
            (observation.source_id, observation.extract_hash_or_snapshot_id): observation.observation_id
            for observation in snapshot.observations
        }
        self._signal_by_observation = {
            signal.observation_id: signal.signal_id for signal in snapshot.signal_inbox
        }

    def require_source(self, source_id: UUID) -> SourceIntelligenceRecord:
        if source_id not in self.sources:
            raise SourceRegistryRuntimeError(f"unknown source: {source_id}")
        return self.sources[source_id]
