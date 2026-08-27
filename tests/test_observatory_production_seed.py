from __future__ import annotations

from pathlib import Path

from apps.api.cognitive_organism_routes import (
    OBSERVATORY_PRODUCTION_SEED_V1,
    seed_observatory_organism_baseline,
)
from brain.adapters.cognition import InMemoryCognitiveOrganismStore
from brain.cognitive_organism import CognitiveOrganism
from tools.seed_observatory_production import (
    BELIEFS,
    EVIDENCE,
    SEED_PACK,
    STIMULI,
    _upsert_system_source,
    sid,
)


class _Result:
    def __init__(self, *, row=None, rowcount: int = 1) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self._row


class _SourceSchemaConnection:
    def __init__(self, *, tenant_scoped: bool) -> None:
        self.tenant_scoped = tenant_scoped
        self.statements: list[str] = []

    def execute(self, statement: str, params=None):
        normalized = " ".join(statement.split())
        self.statements.append(normalized)
        if "information_schema.columns" in normalized:
            return _Result(row=(self.tenant_scoped,))
        return _Result(rowcount=1)


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


def test_source_seed_uses_legacy_conflict_target_before_tenant_scope() -> None:
    conn = _SourceSchemaConnection(tenant_scoped=False)
    assert _upsert_system_source(conn, key="runtime", name="Runtime", trust=0.9) == 1
    write = conn.statements[-1]
    assert "on conflict (key) do update" in write
    assert "where tenant_id is null" not in write


def test_source_seed_uses_system_partial_index_after_tenant_scope() -> None:
    conn = _SourceSchemaConnection(tenant_scoped=True)
    assert _upsert_system_source(conn, key="runtime", name="Runtime", trust=0.9) == 1
    write = conn.statements[-1]
    assert "tenant_id" in write
    assert "on conflict (key) where tenant_id is null do update" in write


def test_seed_replay_preserves_learned_belief_versions() -> None:
    source = Path("tools/seed_observatory_production.py").read_text(encoding="utf-8")
    assert "where public.beliefs.version = 1" in source
    assert "BRAIN_MIGRATION_DATABASE_URL" in source


def test_tenant_runtime_seeds_real_partitions_and_expires_prediction_reads() -> None:
    source = Path("apps/api/tenant_app.py").read_text(encoding="utf-8")
    assert "def _build_organism() -> CognitiveOrganism:" in source
    assert "seed_observatory_organism_baseline(" in source
    assert "TenantPartitionedFactory(_build_organism, evictable=False)" in source
    assert "def _expire_predictions_before_read() -> None:" in source
    assert "base.learning.expire_due_predictions()" in source
