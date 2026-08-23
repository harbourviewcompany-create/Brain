from fastapi import FastAPI
from pydantic import BaseModel, Field

from brain.domain import Evidence
from brain.runtime import BrainRuntime

app = FastAPI(title="Brain Runtime API", version="0.1.0")
runtime = BrainRuntime()


class CreateBeliefRequest(BaseModel):
    statement: str
    confidence: float = Field(default=0.5, ge=0, le=1)


class LearnRequest(BaseModel):
    belief_id: str
    claim: str
    source_id: str
    reliability: float = Field(ge=0, le=1)
    supports: bool


@app.get("/health")
def health():
    return {"status": "ok", "beliefs": len(runtime.store.beliefs), "events": len(runtime.store.events)}


@app.post("/beliefs")
def create_belief(body: CreateBeliefRequest):
    return runtime.create_belief(body.statement, body.confidence)


@app.post("/learn")
def learn(body: LearnRequest):
    from uuid import UUID

    belief = runtime.store.beliefs.get(UUID(body.belief_id))
    if belief is None:
        return {"error": "belief_not_found"}
    evidence = Evidence(claim=body.claim, source_id=body.source_id, reliability=body.reliability)
    return runtime.learn(belief, evidence, body.supports)
