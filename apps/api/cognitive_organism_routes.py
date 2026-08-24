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


def _checkpoint(reason: str) -> None:
    organism_store.save_checkpoint(
        "organism_runtime",
        {
            "reason": reason,
            "cockpit": organism.cockpit(),
            "counts": {
                "self_state_snapshots": len(organism.self_model.snapshots),
                "workspace_items": len(organism.workspace.items),
                "curiosity_tasks": len(organism.curiosity.tasks),
                "original_ideas": len(organism.originality.ideas),
                "dream_insights": len(organism.dreams.insights),
                "debates": len(organism.debates.debates),
                "quarantine_items": len(organism.immune.quarantine),
                "agency_actions": len(organism.agency.actions),
                "development_events": len(organism.development.events),
            },
        },
    )


def register_cognitive_organism_routes(app: FastAPI) -> None:
    @app.get("/organism/self-state")
    def organism_self_state():
        return encode(organism.self_model.current)

    @app.get("/organism/goals")
    def organism_goals():
        return encode({"items": list(organism.goals.goals.values()), "tension": organism.goals.tension_report()})

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
        return encode({"cycles": organism.dreams.cycles, "insights": organism.dreams.insights})

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
        return {"admitted": admitted, "item": encode(item), "workspace": organism.workspace.snapshot()}

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
        cycle, insight = organism.dreams.run(body.memory_refs, body.signal_refs, body.repeated_patterns)
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
