from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_MODULES = [
    "brain/agency.py",
    "brain/cognitive_immune.py",
    "brain/cognitive_organism.py",
    "brain/development.py",
    "brain/global_workspace.py",
    "brain/goals.py",
    "brain/imagination.py",
    "brain/originality_engine.py",
    "brain/self_model.py",
]


REQUIRED_FIXTURES = [
    "self_state_snapshot.json",
    "goal_pressure_competition.json",
    "global_workspace_focus.json",
    "curiosity_from_uncertainty.json",
    "original_idea_from_memory.json",
    "dream_consolidation_cycle.json",
    "internal_debate.json",
    "immune_quarantine.json",
    "agency_policy_boundary.json",
    "development_event.json",
]


def test_traceability_includes_all_new_brain_modules():
    matrix = (ROOT / "docs/control/module-build-ready-traceability.md").read_text(encoding="utf-8")
    registry = (ROOT / "docs/control/source-requirement-registry.json").read_text(encoding="utf-8")
    for module in REQUIRED_MODULES:
        assert module in matrix
        assert module in registry
    assert "COGNITIVE-ORGANISM-V1" in (ROOT / "reports/acceptance/COGNITIVE-ORGANISM-V1.json").read_text(encoding="utf-8")


def test_cognitive_organism_fixtures_are_materialized():
    fixture_dir = ROOT / "tests/fixtures/cognitive_organism"
    for fixture in REQUIRED_FIXTURES:
        text = (fixture_dir / fixture).read_text(encoding="utf-8")
        assert "fixture_id" in text
        assert "expected" in text


def test_cognitive_organism_audit_note_exists():
    note = (ROOT / "reports/acceptance/COGNITIVE-ORGANISM-V1-AUDIT-NOTE.md").read_text(encoding="utf-8")
    assert "SOURCE material remains preserved" in note
    assert "Tier 5 autonomy remains HOLD" in note
