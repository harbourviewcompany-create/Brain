"""Reasoning port for endogenous cognition."""
from __future__ import annotations
import json, os, re, urllib.error, urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4
from .model_cortex import ModelCortexRouter, ModelOutput, ModelProfile, ModelRoute

@dataclass(slots=True)
class ReasonRequest:
    task_type: str
    prompt: str
    context: dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 400

@dataclass(slots=True)
class ReasonResult:
    content: str
    confidence: float
    task_type: str
    model_id: str
    evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

class Reasoner(Protocol):
    def reason(self, request: ReasonRequest) -> ReasonResult: ...

class LocalHeuristicReasoner:
    model_id: str = "local-heuristic-v1"
    def reason(self, request: ReasonRequest) -> ReasonResult:
        ctx = request.context or {}
        if request.task_type == "curiosity_answer":
            return self._curiosity(request, ctx)
        if request.task_type == "contradiction":
            return self._contradiction(request, ctx)
        if request.task_type == "dream_skeptic":
            return self._dream_skeptic(request, ctx)
        return self._general(request, ctx)
    def _curiosity(self, request: ReasonRequest, ctx: dict[str, Any]) -> ReasonResult:
        question = str(ctx.get("question") or request.prompt)
        beliefs = ctx.get("belief_statements") or []
        unknowns = ctx.get("related_unknowns") or []
        lines = [f"Question under investigation: {question}", "Working answer (provisional, evidence-bounded):"]
        if beliefs:
            lines.append(f"- Current belief context ({len(beliefs)} statements): " + "; ".join(str(b)[:80] for b in beliefs[:3]))
            lines.append("- Inference: the question is open because supporting evidence is incomplete or confidence is below establishment threshold.")
        else:
            lines.append("- Inference: sparse prior; default to high uncertainty.")
        if unknowns:
            lines.append("- Related unknowns: " + "; ".join(str(u)[:60] for u in unknowns[:3]))
        lines.append("- Falsification: disconfirm if reliable contradictory evidence arrives with higher weight than current support.")
        lines.append("- Next observation needed: targeted evidence that would raise or lower confidence by >= 0.15.")
        return ReasonResult(content="\n".join(lines), confidence=0.45, task_type=request.task_type, model_id=self.model_id, metadata={"reasoner": "local_heuristic", "mode": "curiosity"})
    def _contradiction(self, request: ReasonRequest, ctx: dict[str, Any]) -> ReasonResult:
        statement = str(ctx.get("statement") or request.prompt)
        supporting = int(ctx.get("supporting") or 0)
        contradicting = int(ctx.get("contradicting") or 0)
        confidence = float(ctx.get("confidence") or 0.5)
        lines = [
            f"Contested belief: {statement}",
            f"- Support count: {supporting}; Contradict count: {contradicting}; Prior confidence: {confidence:.2f}",
            "- Diagnosis: " + ("material conflict — reduce confidence and open investigation." if contradicting > supporting else "tension present but support still leads."),
            "- Resolution path: gather one high-reliability observation that uniquely favors one side.",
            "- Interim: hold belief as provisional; do not promote to established.",
        ]
        conf = max(0.2, min(0.7, confidence - 0.1 * max(0, contradicting - supporting)))
        return ReasonResult(content="\n".join(lines), confidence=conf, task_type=request.task_type, model_id=self.model_id, metadata={"reasoner": "local_heuristic", "mode": "contradiction"})
    def _dream_skeptic(self, request: ReasonRequest, ctx: dict[str, Any]) -> ReasonResult:
        hyp = str(ctx.get("hypothesis") or request.prompt)
        dream_conf = float(ctx.get("dream_confidence") or 0.4)
        lines = [
            f"Skeptic review of dream hypothesis: {hyp}",
            f"- Dream confidence claim: {dream_conf:.2f}",
            "- Verdict: retain as speculative hypothesis only; require waking evidence before belief update.",
            "- Risk: recombination can invent structure not present in sources.",
            "- Gate: promotion requires independent observation or successful prediction.",
        ]
        return ReasonResult(content="\n".join(lines), confidence=min(0.4, dream_conf * 0.5), task_type=request.task_type, model_id=self.model_id, metadata={"reasoner": "local_heuristic", "mode": "dream_skeptic", "verdict": "hold_as_hypothesis"})
    def _general(self, request: ReasonRequest, ctx: dict[str, Any]) -> ReasonResult:
        return ReasonResult(content=f"Structured reflection on: {request.prompt[:200]}\n- Status: acknowledged; no external model invoked.\n- Action: keep as working note until evidence arrives.", confidence=0.35, task_type=request.task_type, model_id=self.model_id, metadata={"reasoner": "local_heuristic", "mode": "general"})

class HttpLLMReasoner:
    def __init__(self, *, base_url: str | None = None, api_key: str | None = None, model: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or os.environ.get("BRAIN_LLM_URL") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("BRAIN_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        self.model = model or os.environ.get("BRAIN_LLM_MODEL") or "gpt-4o-mini"
        self.timeout = timeout
        self.model_id = f"http:{self.model}"
    @property
    def available(self) -> bool:
        return bool(self.base_url or self.api_key)
    def reason(self, request: ReasonRequest) -> ReasonResult:
        if not self.available:
            return LocalHeuristicReasoner().reason(request)
        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        system = "You are the Brain reasoning cortex. Be concise, evidence-aware, and mark uncertainty. Prefer structured bullet answers."
        user = f"Task: {request.task_type}\nPrompt: {request.prompt}\nContext: {json.dumps(request.context)[:2000]}"
        body = json.dumps({"model": self.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "max_tokens": request.max_tokens, "temperature": 0.3}).encode()
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode())
            content = payload["choices"][0]["message"]["content"]
            return ReasonResult(content=content, confidence=0.55, task_type=request.task_type, model_id=self.model_id, metadata={"reasoner": "http_llm", "raw_keys": list(payload.keys())})
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError, json.JSONDecodeError) as exc:
            fallback = LocalHeuristicReasoner().reason(request)
            fallback.metadata["llm_error"] = repr(exc)
            fallback.metadata["fell_back"] = True
            return fallback

class CortexReasoner:
    def __init__(self) -> None:
        self.router = ModelCortexRouter()
        self.local = LocalHeuristicReasoner()
        self.http = HttpLLMReasoner()
        local_profile = ModelProfile(provider="local", model="heuristic-v1", task_strengths={"curiosity_answer": 0.7, "contradiction": 0.75, "dream_skeptic": 0.8, "general": 0.6}, calibration=0.6, historical_accuracy=0.55, latency_score=0.95, cost_score=0.95)
        self.router.register(local_profile)
        self._local_id = local_profile.id
        if self.http.available:
            http_profile = ModelProfile(provider="http", model=self.http.model, task_strengths={"curiosity_answer": 0.85, "contradiction": 0.85, "dream_skeptic": 0.8, "general": 0.9}, calibration=0.55, historical_accuracy=0.6, latency_score=0.4, cost_score=0.3)
            self.router.register(http_profile)
            self._http_id = http_profile.id
        else:
            self._http_id = None
    def reason(self, request: ReasonRequest) -> ReasonResult:
        route = self.router.route(request.task_type, cost_priority=0.4, latency_priority=0.5)
        use_http = self._http_id is not None and route.model_id == self._http_id and self.http.available
        result = self.http.reason(request) if use_http else self.local.reason(request)
        result.metadata["route_score"] = route.score
        result.metadata["routed_model"] = str(route.model_id)
        return result

def default_reasoner() -> CortexReasoner:
    return CortexReasoner()
