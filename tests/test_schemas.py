from pydantic import ValidationError
import pytest

from brain.schemas import CANONICAL_SCHEMAS, Source, validate_object


REQUIRED_SCHEMA_NAMES = {
    "Source",
    "Sensor",
    "RawObservation",
    "PerceptualEvent",
    "EvidenceItem",
    "Entity",
    "Belief",
    "Signal",
    "Opportunity",
    "CandidateAction",
    "ApprovalRequest",
    "Outcome",
    "Prediction",
    "RewardEvent",
    "PainEvent",
    "MemoryObject",
    "GraphNode",
    "GraphEdge",
    "FormulaRun",
    "DecisionExplanation",
    "AcceptanceReport",
}


def test_all_canonical_objects_have_executable_schemas():
    assert REQUIRED_SCHEMA_NAMES <= set(CANONICAL_SCHEMAS)


def test_schema_required_fields_are_enforced():
    with pytest.raises(ValidationError):
        Source.model_validate({"kind": "registry", "trust_score": 0.7})


def test_schema_enum_validation_is_enforced():
    with pytest.raises(ValidationError):
        validate_object(
            "ApprovalRequest",
            {
                "action_id": "action-1",
                "state": "silently_approved",
                "required_approver": "operator",
            },
        )


def test_schema_provenance_fields_are_preserved():
    source = Source.model_validate(
        {
            "name": "Regulator registry",
            "kind": "registry",
            "trust_score": 0.9,
            "source_refs": ["docs/brain-readable-concept-manual.md"],
            "provenance": [{"source_id": "manual", "source_location": "section-5"}],
        }
    )
    assert source.source_refs == ["docs/brain-readable-concept-manual.md"]
    assert source.provenance[0].source_id == "manual"
    for schema in CANONICAL_SCHEMAS.values():
        assert "source_refs" in schema.model_fields
        assert "provenance" in schema.model_fields
