from __future__ import annotations

from apps.api.cognitive_organism_routes import (
    OBSERVATORY_PRODUCTION_SEED_V1,
    seed_observatory_organism_baseline,
)
from brain.adapters.cognition import InMemoryCognitiveOrganismStore
from brain.cognitive_organism import CognitiveOrganism
from tools.seed_observatory_production import BELIEFS, EVIDENCE, SEED_PACK, STIMULI, sid


def test_seed_pack_ids_are_stable_and_unique() -> None:
    keys = [
        *(f"belief:{belief.key}" for belief in BELIEFS),
        *(f"evidence:{item[1]}" for item in EVIDENCE),
        *(f"inbox:{item[0]}" for item in STIMULI),
    ]
    ids = [sid(key) for key in keys]
    assert len(ids) == len(set(ids))
    assert ids == [sid(key) for key in keys]
    assert SEED_PACK == OBSERVATORY_PRODUCTION_SEED_V1


def test_seed_beliefs_include_unknowns_and_a_contested_hypothesis() -> None:
    assert all(belief.unknowns for belief in BELIEFS)
    contested = [belief for belief in BELIEFS if belief.state == "contested"]
    assert len(contested) == 1
    assert "dedicated worker" in contested[0].statement.lower()


def test_organism_baseline_is_explicit_rich_and_idempotent() -> None:
    target = CognitiveOrganism()
    store = InMemoryCognitiveOrganismStore()

    assert seed_observatory_organism_baseline(
        target=target,
        store=store,
        seed_pack=OBSERVATORY_PRODUCTION_SEED_V1,
    )

    current = target.self_model.current
    assert current is not None
    assert current.current_focus_summary == "Production cognition baseline and verified data flow"
    assert current.metadata["seed_pack"] == OBSERVATORY_PRODUCTION_SEED_V1
    assert current.metadata["external_intelligence"] is False
    assert len(target.curiosity.tasks) == 3
    assert len(target.agency.actions) == 1
    assert len(target.immune.quarantine) == 1
    assert target.workspace.snapshot()["active_focus"]

    checkpoint = store.load_checkpoint("organism_runtime")
    assert checkpoint is not None
    assert checkpoint["seed_pack"] == OBSERVATORY_PRODUCTION_SEED_V1
    assert checkpoint["cockpit"]["self_state"] is not None
    assert checkpoint["cockpit"]["curiosity_queue"]

    assert not seed_observatory_organism_baseline(
        target=target,
        store=store,
        seed_pack=OBSERVATORY_PRODUCTION_SEED_V1,
    )
    assert len(target.curiosity.tasks) == 3


def test_organism_baseline_is_opt_in() -> None:
    target = CognitiveOrganism()
    store = InMemoryCognitiveOrganismStore()
    assert not seed_observatory_organism_baseline(
        target=target,
        store=store,
        seed_pack="disabled",
    )
    assert target.self_model.current is None
    assert store.load_checkpoint("organism_runtime") is None
