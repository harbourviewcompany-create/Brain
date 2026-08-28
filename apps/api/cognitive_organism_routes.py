from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from brain.adapters.cognition import InMemoryCognitiveOrganismStore, PostgresCognitiveOrganismStore
from brain.cognitive_organism import AgencyTier, CognitiveOrganism, GlobalWorkspaceItem

OBSERVATORY_PRODUCTION_SEED_V1 = "observatory-production-seed-v1"

organism = CognitiveOrganism()


class SelfStateUpdateRequest(BaseModel):
    current_focus_summary: str
    belief_count: int = Field(default=0, ge=0)
    event_count: int = Field(default=0, ge=0)
    prediction_count: int = Field(default=0, ge=0)
    opportunity_count: int = Field(default=0, ge=0)
    uncertainty_load: float = Field(default=0.0, ge=0, le=1)
    contradiction_load: float = Field(default=0.0, ge=0, le=1)
    curiosity_pressure: float = Field(default=0.0, ge=0, le=1)
    revenue_pressure: float = Field(default=0.0, ge=0, le=1)
    risk_pressure: float = Field(default=0.0, ge=0, le=1)
    memory_pressure: float = Field(default=0.0, ge=0, le=1)
    action_backlog_pressure: float = Field(default=0.0, ge=0, le=1)
    source_event_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceAdmitRequest(BaseModel):
    title: str
    content: str
    item_type: str = "signal"
    source_refs: list[str] = Field(default_factory=list)
    salience: float = Field(default=0.5, ge=0, le=1)
    novelty: float = Field(default=0.0, ge=0, le=1)
    urgency: float = Field(default=0.0, ge=0, le=1)
    risk: float = Field(default=0.0, ge=0, le=1)
    goal_pressure: float = Field(default=0.0, ge=0, le=1)


class CuriosityGenerateRequest(BaseModel):
    trigger_type: str
    trigger_refs: list[str] = Field(default_factory=list)
    question: str
    expected_value: float = Field(default=0.5, ge=0, le=1)
    uncertainty: float = Field(default=0.7, ge=0, le=1)
    cost: float = Field(default=0.15, ge=0, le=1)
    falsification_condition: str | None = None


class OriginalIdeaGenerateRequest(BaseModel):
    title: str
    idea: str
    source_signal_refs: list[str]
    memory_refs: list[str]
    combination_method: str
    why_most_people_miss_it: str
    fastest_test: str
    kill_condition: str
    risk_score: float = Field(default=0.2, ge=0, le=1)


class DreamRunRequest(BaseModel):
    memory_refs: list[str] = Field(default_factory=list)
    signal_refs: list[str] = Field(default_factory=list)
    repeated_patterns: list[str] = Field(default_factory=list)


class DebateRequest(BaseModel):
    topic: str
    proposal: str
    evidence_refs: list[str] = Field(default_factory=list)
    risk: float = Field(default=0.2, ge=0, le=1)
    proposal_type: str = "idea"


class ImmuneScreenRequest(BaseModel):
    item_type: str
    item_ref: str
    claims: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0, le=1)
    external_action: bool = False


class AgencyProposeRequest(BaseModel):
    action_type: str
    proposal: str
    tier: str = "tier_3_recommend"
    source_refs: list[str] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0, le=1)


class AgencyApproveRequest(BaseModel):
    action_id: str
    approved_by: str


def _configure_persistence_store() -> InMemoryCognitiveOrganismStore | PostgresCognitiveOrganismStore:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return InMemoryCognitiveOrganismStore()
    try:
        return PostgresCognitiveOrganismStore(dsn)
    except Exception:
        return InMemoryCognitiveOrganismStore()


organism_store = _configure_persistence_store()
startup_checkpoint = organism_store.load_checkpoint("organism_runtime")
organism_store.append_audit_event(
    "COGNITIVE_ORGANISM_ROUTE_BOOTSTRAPPED",
    "cognitive_organism_runtime",
    "organism_runtime",
    {"rehydrated_checkpoint": startup_checkpoint is not None},
)


def encode(value: Any) -> Any:
    if is_dataclass(value):
        return jsonable_encoder(asdict(value))
    return jsonable_encoder(value)


def _checkpoint_payload(target: CognitiveOrganism, reason: str) -> dict[str, Any]:
    return {
        "reason": reason,
        "cockpit": target.cockpit(),
        "counts": {
            "self_state_snapshots": len(target.self_model.snapshots),
            "workspace_items": len(target.workspace.items),
            "curiosity_tasks": len(target.curiosity.tasks),
            "original_ideas": len(target.originality.ideas),
            "dream_insights": len(target.dreams.insights),
            "debates": len(target.debates.debates),
            "quarantine_items": len(target.immune.quarantine),
            "agency_actions": len(target.agency.actions),
            "development_events": len(target.development.events),
        },
    }


def _checkpoint(reason: str) -> None:
    organism_store.save_checkpoint(
        "organism_runtime",
        _checkpoint_payload(organism, reason),
    )


def seed_observatory_organism_baseline(
    *,
    target: CognitiveOrganism | None = None,
    store: InMemoryCognitiveOrganismStore | PostgresCognitiveOrganismStore | None = None,
    seed_pack: str | None = None,
) -> bool:
    """Initialize a transparent production baseline for the process-local organism.

    The durable seed script populates PostgreSQL read models. The CognitiveOrganism
    is intentionally process-local today, so without an explicit startup baseline
    a restart still rendered SELF STATE NOT SNAPSHOTTED even while the database
    was populated. This baseline uses only internal system facts and architecture
    questions; it never represents seeded material as external intelligence.
    """

    requested = (
        seed_pack
        if seed_pack is not None
        else (os.environ.get("BRAIN_OBSERVATORY_SEED_PACK") or "").strip()
    )
    if requested != OBSERVATORY_PRODUCTION_SEED_V1:
        return False

    target = target or organism
    store = store or organism_store
    if target.self_model.current is not None:
        return False

    refs = [
        "seed:production-runtime",
        "seed:observatory-runtime",
        "seed:repository-contract",
    ]
    focus = GlobalWorkspaceItem(
        item_type="system_baseline",
        title="Production cognition baseline",
        content=(
            "Validate live transport, durable state, cognition continuity, and the next "
            "verified-source ingestion improvements."
        ),
        source_refs=refs,
        salience=0.88,
        novelty=0.58,
        urgency=0.66,
        risk=0.12,
        goal_pressure=target.goals.dominant_goal().pressure,
    )
    target.admit_workspace_item(focus)

    target.curiosity.generate(
        "production_baseline",
        refs,
        "Which remaining cognition projections still depend on process-local state?",
        expected_value=0.90,
        uncertainty=0.72,
        cost=0.10,
        falsification_condition="Resolve when every displayed projection survives process replacement.",
    )
    target.curiosity.generate(
        "source_quality",
        ["seed:repository-contract"],
        "Which approved source classes produce the highest information gain per unit cost?",
        expected_value=0.88,
        uncertainty=0.80,
        cost=0.18,
        falsification_condition="Reject a source class when measured freshness and utility remain below threshold.",
    )
    target.curiosity.generate(
        "worker_architecture",
        ["seed:production-runtime"],
        "When does production load justify moving lease-controlled cognition to a dedicated worker?",
        expected_value=0.76,
        uncertainty=0.62,
        cost=0.12,
    )

    target.immune.screen(
        item_type="production_release",
        item_ref="tenant-rls-019-022",
        claims=["Tenant RLS release changes production authorization and data ownership boundaries."],
        evidence_refs=["seed:deployment-control"],
        risk_score=0.68,
        external_action=True,
    )
    target.agency.propose(
        action_type="prioritize_verified_source_ingestion",
        proposal=(
            "Prioritize verified source ingestion after baseline cognition is stable; "
            "keep external actions approval-gated."
        ),
        tier=AgencyTier.TIER_3_RECOMMEND,
        source_refs=refs,
        risk_score=0.10,
    )

    target.update_self_state(
        current_focus_summary="Production cognition baseline and verified data flow",
        belief_count=5,
        event_count=9,
        prediction_count=3,
        opportunity_count=0,
        uncertainty_load=0.34,
        contradiction_load=0.28,
        curiosity_pressure=0.72,
        revenue_pressure=0.22,
        risk_pressure=0.18,
        memory_pressure=0.20,
        action_backlog_pressure=0.16,
        source_event_ids=refs,
        metadata={
            "seed_pack": OBSERVATORY_PRODUCTION_SEED_V1,
            "external_intelligence": False,
            "purpose": "production_observability_baseline",
        },
    )

    payload = _checkpoint_payload(target, OBSERVATORY_PRODUCTION_SEED_V1)
    payload["seed_pack"] = OBSERVATORY_PRODUCTION_SEED_V1
    store.save_checkpoint("organism_runtime", payload)
    store.append_audit_event(
        "OBSERVATORY_ORGANISM_BASELINE_INITIALIZED",
        "seed_pack",
        OBSERVATORY_PRODUCTION_SEED_V1,
        {
            "seed_pack": OBSERVATORY_PRODUCTION_SEED_V1,
            "external_intelligence": False,
        },
    )
    return True


# Production bootstrap is explicitly opt-in by environment variable. Tests and
# unconfigured environments remain unchanged.
seed_observatory_organism_baseline()


def register_cognitive_organism_routes(app: FastAPI) -> None:
    @app.get("/organism/self-state")
    def organism_self_state():
        return encode(organism.self_model.current)

    @app.get("/organism/goals")
    def organism_goals():
        return encode(
            {
                "items": list(organism.goals.goals.values()),
                "tension": organism.goals.tension_report(),
            }
        )

    @app.get("/organism/workspace")
    def organism_workspace():
        return organism.workspace.snapshot()

    @app.get("/organism/curiosity")
    def organism_curiosity():
        return encode({"items": organism.curiosity.tasks})

    @app.get("/organism/original-ideas")
    def organism_original_ideas():
        return encode({"items": organism.originality.ideas})

    @app.get("/organism/dreams")
    def organism_dreams():
        return encode(
            {"cycles": organism.dreams.cycles, "insights": organism.dreams.insights}
        )

    @app.get("/organism/debates")
    def organism_debates():
        return encode({"items": organism.debates.debates})

    @app.get("/organism/quarantine")
    def organism_quarantine():
        return encode({"items": organism.immune.quarantine})

    @app.get("/organism/agency-actions")
    def organism_agency_actions():
        return encode({"items": list(organism.agency.actions.values())})

    @app.get("/organism/development-timeline")
    def organism_development_timeline():
        return encode({"items": organism.development.events})

    @app.get("/organism/cockpit")
    def organism_cockpit():
        return organism.cockpit()

    @app.get("/organism/persistence/status")
    def organism_persistence_status():
        return {
            "store": type(organism_store).__name__,
            "checkpoint_name": "organism_runtime",
            "has_startup_checkpoint": startup_checkpoint is not None,
            "autonomy_boundary": "persistence_only_no_external_action",
        }

    @app.get("/organism/persistence/checkpoint")
    def organism_persistence_checkpoint():
        return {"checkpoint": organism_store.load_checkpoint("organism_runtime")}

    @app.post("/organism/persistence/checkpoint")
    def organism_persistence_checkpoint_now():
        _checkpoint("operator_requested_checkpoint")
        return {"checkpoint": organism_store.load_checkpoint("organism_runtime")}

    @app.post("/organism/persistence/rehydrate")
    def organism_persistence_rehydrate():
        checkpoint = organism_store.load_checkpoint("organism_runtime")
        organism_store.append_audit_event(
            "COGNITIVE_ORGANISM_REHYDRATE_REQUESTED",
            "cognitive_organism_checkpoint",
            "organism_runtime",
            {"checkpoint_found": checkpoint is not None},
        )
        return {"rehydrated": checkpoint is not None, "checkpoint": checkpoint}

    @app.get("/organism/audit-events")
    def organism_audit_events(limit: int = 50):
        return {"items": organism_store.list_audit_events(limit=limit)}

    @app.post("/organism/self-state/update")
    def organism_update_self_state(body: SelfStateUpdateRequest):
        result = organism.update_self_state(**body.model_dump())
        _checkpoint("self_state_update")
        return encode(result)

    @app.post("/organism/workspace/admit")
    def organism_admit_workspace(body: WorkspaceAdmitRequest):
        item = GlobalWorkspaceItem(**body.model_dump())
        admitted = organism.admit_workspace_item(item)
        _checkpoint("workspace_admit")
        return {
            "admitted": admitted,
            "item": encode(item),
            "workspace": organism.workspace.snapshot(),
        }

    @app.post("/organism/curiosity/generate")
    def organism_generate_curiosity(body: CuriosityGenerateRequest):
        result = organism.curiosity.generate(**body.model_dump())
        _checkpoint("curiosity_generate")
        return encode(result)

    @app.post("/organism/original-ideas/generate")
    def organism_generate_original_idea(body: OriginalIdeaGenerateRequest):
        result = organism.generate_original_idea(**body.model_dump())
        _checkpoint("original_idea_generate")
        return encode(result)

    @app.post("/organism/dream/run")
    def organism_run_dream(body: DreamRunRequest):
        cycle, insight = organism.dreams.run(
            body.memory_refs, body.signal_refs, body.repeated_patterns
        )
        _checkpoint("dream_run")
        return {"cycle": encode(cycle), "insight": encode(insight)}

    @app.post("/organism/debate")
    def organism_debate(body: DebateRequest):
        result = organism.debates.debate(**body.model_dump())
        _checkpoint("debate")
        return encode(result)

    @app.post("/organism/immune/screen")
    def organism_immune_screen(body: ImmuneScreenRequest):
        result = organism.immune.screen(**body.model_dump())
        _checkpoint("immune_screen")
        return encode(result)

    @app.post("/organism/agency/propose")
    def organism_agency_propose(body: AgencyProposeRequest):
        data = body.model_dump()
        data["tier"] = AgencyTier(data["tier"])
        result = organism.agency.propose(**data)
        _checkpoint("agency_propose")
        return encode(result)

    @app.post("/organism/agency/approve")
    def organism_agency_approve(body: AgencyApproveRequest):
        result = organism.agency.approve(UUID(body.action_id), body.approved_by)
        _checkpoint("agency_approve")
        return encode(result)
