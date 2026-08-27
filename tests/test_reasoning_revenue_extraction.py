"""LocalHeuristicReasoner / CortexReasoner: revenue_entity_extraction task."""

from __future__ import annotations

import json

from brain.reasoning import (
    CortexReasoner,
    HttpLLMReasoner,
    LocalHeuristicReasoner,
    ReasonRequest,
)


def test_local_heuristic_extracts_email_as_low_confidence_contact():
    reasoner = LocalHeuristicReasoner()
    request = ReasonRequest(
        task_type="revenue_entity_extraction",
        prompt="Contact us at buyer@example.com for details",
        context={"raw_text": "Contact us at buyer@example.com for details"},
    )
    result = reasoner.reason(request)
    parsed = json.loads(result.content)
    assert parsed["contact_channel"]["value"] == "buyer@example.com"
    assert parsed["contact_channel"]["confidence"] < 0.5


def test_local_heuristic_never_invents_a_name():
    reasoner = LocalHeuristicReasoner()
    request = ReasonRequest(
        task_type="revenue_entity_extraction",
        prompt="City government issues request for proposal for qualified vendors",
        context={"raw_text": "City government issues request for proposal for qualified vendors"},
    )
    result = reasoner.reason(request)
    parsed = json.loads(result.content)
    assert "named_buyer" not in parsed
    assert "decision_maker" not in parsed
    assert "payment_path" not in parsed


def test_local_heuristic_returns_empty_object_when_nothing_found():
    reasoner = LocalHeuristicReasoner()
    request = ReasonRequest(
        task_type="revenue_entity_extraction",
        prompt="It rained heavily today",
        context={"raw_text": "It rained heavily today"},
    )
    result = reasoner.reason(request)
    assert json.loads(result.content) == {}
    assert result.confidence <= 0.1


def test_http_llm_reasoner_uses_strict_extraction_system_prompt():
    prompt = HttpLLMReasoner.SYSTEM_PROMPTS["revenue_entity_extraction"]
    assert "must NOT invent" in prompt
    assert "JSON" in prompt


def test_cortex_router_registers_revenue_entity_extraction_task():
    cortex = CortexReasoner()
    local_profile = cortex.router.models[cortex._local_id]
    assert "revenue_entity_extraction" in local_profile.task_strengths
    # Local heuristic is deliberately weak at this task (regex-only);
    # it should route to the (unavailable-by-default-in-tests) HTTP
    # profile only when one is actually configured. Absent BRAIN_LLM_URL
    # / BRAIN_LLM_API_KEY / OPENAI_API_KEY in the test environment,
    # local is the only registered model.
    if cortex._http_id is None:
        result = cortex.reason(ReasonRequest(
            task_type="revenue_entity_extraction", prompt="x", context={"raw_text": "x"},
        ))
        assert result.metadata["reasoner"] == "local_heuristic"
