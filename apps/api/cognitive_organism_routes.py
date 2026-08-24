from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

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


def encode(value: Any) -> Any:
    if is_dataclass(value):
        return jsonable_encoder(asdict(value))
    return jsonable_encoder(value)


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

    @app.post("/organism/self-state/update")
    def organism_update_self_state(body: SelfStateUpdateRequest):
        return encode(organism.update_self_state(**body.model_dump()))

    @app.post("/organism/workspace/admit")
    def organism_admit_workspace(body: WorkspaceAdmitRequest):
        item = GlobalWorkspaceItem(**body.model_dump())
        admitted = organism.admit_workspace_item(item)
        return {"admitted": admitted, "item": encode(item), "workspace": organism.workspace.snapshot()}

    @app.post("/organism/curiosity/generate")
    def organism_generate_curiosity(body: CuriosityGenerateRequest):
        return encode(organism.curiosity.generate(**body.model_dump()))

    @app.post("/organism/original-ideas/generate")
    def organism_generate_original_idea(body: OriginalIdeaGenerateRequest):
        return encode(organism.generate_original_idea(**body.model_dump()))

    @app.post("/organism/dream/run")
    def organism_run_dream(body: DreamRunRequest):
        cycle, insight = organism.dreams.run(body.memory_refs, body.signal_refs, body.repeated_patterns)
        return {"cycle": encode(cycle), "insight": encode(insight)}

    @app.post("/organism/debate")
    def organism_debate(body: DebateRequest):
        return encode(organism.debates.debate(**body.model_dump()))

    @app.post("/organism/immune/screen")
    def organism_immune_screen(body: ImmuneScreenRequest):
        return encode(organism.immune.screen(**body.model_dump()))

    @app.post("/organism/agency/propose")
    def organism_agency_propose(body: AgencyProposeRequest):
        data = body.model_dump()
        data["tier"] = AgencyTier(data["tier"])
        return encode(organism.agency.propose(**data))

    @app.post("/organism/agency/approve")
    def organism_agency_approve(body: AgencyApproveRequest):
        return encode(organism.agency.approve(UUID(body.action_id), body.approved_by))
