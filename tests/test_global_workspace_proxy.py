import json
from pathlib import Path

import pytest

from brain.developmental.global_workspace import GlobalWorkspaceService

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "neuroscience" / "json" / "global-workspace-proxy.json"
FIXTURE = ROOT / "tests" / "fixtures" / "neuro" / "global_workspace_frame.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_global_workspace_registry_has_required_objects() -> None:
    data = load_json(REGISTRY)
    fixture = load_json(FIXTURE)
    object_ids = {item["object_id"] for item in data["objects"]}

    assert set(fixture["expected"]["required_objects"]).issubset(object_ids)
    assert data["runtime_anchor"] == "brain.developmental.global_workspace.GlobalWorkspaceService"
    assert "phenomenal consciousness" in data["non_claims"]
    assert data["dashboard"] == "Global Workspace Viewer"


def test_workspace_service_selects_winner_and_preserves_suppressed_alternatives() -> None:
    fixture = load_json(FIXTURE)
    service = GlobalWorkspaceService()

    service.propose_item(
        content_ref="signal:background",
        priority=0.25,
        evidence_refs=["evidence:background"],
        proposing_module="perception",
    )
    service.propose_item(
        content_ref=fixture["expected"]["winner_content_ref"],
        priority=0.95,
        evidence_refs=["evidence:contradiction"],
        proposing_module="salience",
    )
    service.propose_item(
        content_ref="signal:research-debt",
        priority=0.35,
        evidence_refs=["evidence:research"],
        proposing_module="unknown_mechanism",
    )

    cycle = service.compete_and_broadcast(
        consumer_modules=fixture["expected"]["consumer_modules"],
    )
    broadcast = service.broadcasts[-1]

    assert cycle.winner_id == broadcast.winner_id
    assert len(cycle.suppressed_item_ids) == fixture["expected"]["suppressed_count"]
    assert broadcast.consumer_modules == fixture["expected"]["consumer_modules"]
    assert broadcast.consciousness_claim is fixture["expected"]["consciousness_claim"]
    assert broadcast.evidence_refs == ["evidence:contradiction"]
    assert service.items == []


def test_workspace_service_fails_closed_without_evidence_or_consumers() -> None:
    service = GlobalWorkspaceService()

    with pytest.raises(ValueError, match="workspace_item_requires_evidence"):
        service.propose_item(
            content_ref="signal:unsupported",
            priority=0.9,
            evidence_refs=[],
            proposing_module="perception",
        )

    service.propose_item(
        content_ref="signal:supported",
        priority=0.9,
        evidence_refs=["evidence:supported"],
        proposing_module="perception",
    )

    with pytest.raises(ValueError, match="broadcast_requires_consumers"):
        service.compete_and_broadcast(consumer_modules=[])


def test_registry_blocks_consciousness_claims() -> None:
    data = load_json(REGISTRY)
    forbidden = " ".join(data["non_claims"]).lower()

    assert "consciousness" in forbidden
    assert "sentience" in forbidden
    assert all(item["go_hold_status"] in {"GO", "HOLD"} for item in data["objects"])
    assert not any(item.get("consciousness_claim") is True for item in data["objects"])
