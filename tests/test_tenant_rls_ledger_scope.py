"""The tenant-RLS gate must not fail because a newer migration exists.

`verify_tenant_rls_release.py` requires every migration it expects to be
present in `brain_schema_migrations`. It derived that expectation by globbing
every `.sql` on disk, while the PR126 workflow deliberately migrates only to
version 22 so it can prove 019-022 apply in order over a pre-tenant baseline.

The first migration numbered above the cap therefore failed the gate:

    RuntimeError: migration ledger missing: 023_revenue_source_scores.sql

That is the verifier reporting its own scope, not a broken release contract.
The expectation is now bounded by the same cap the caller migrates to, and the
two must stay in step -- which is what the workflow test below pins.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.verify_tenant_rls_release import _migration_hashes, _migration_version

REPO_ROOT = Path(__file__).resolve().parents[1]
PR126_WORKFLOW = REPO_ROOT / ".github/workflows/verify-pr126-tenant-release-fix.yml"


def test_uncapped_expectation_still_covers_every_migration():
    names = set(_migration_hashes())
    on_disk = {p.name for p in (REPO_ROOT / "db/migrations").glob("*.sql")}
    assert names == on_disk


def test_cap_excludes_migrations_above_it():
    capped = _migration_hashes(22)
    assert capped, "expected migrations at or below 22"
    assert all(_migration_version(name) <= 22 for name in capped)
    assert set(_migration_hashes()) - set(capped) == {
        name for name in _migration_hashes() if _migration_version(name) > 22
    }


def test_a_migration_above_the_cap_does_not_break_the_capped_expectation():
    """The exact CI failure: ledger has 001..22, disk also has 023+."""
    applied = {name for name in _migration_hashes() if _migration_version(name) <= 22}
    assert not set(_migration_hashes(22)) - applied
    above = sorted(set(_migration_hashes()) - applied)
    if above:
        assert set(_migration_hashes()) - applied == set(above), (
            "uncapped expectation still demands migrations the workflow never applies"
        )


def test_workflow_verifies_the_same_version_it_migrates_to():
    """Bumping one cap without the other silently reopens this failure."""
    source = PR126_WORKFLOW.read_text(encoding="utf-8")

    applied = {
        int(m) for m in re.findall(r"apply_migrations\.py --max-version (\d+)", source)
    }
    verified = {
        int(m)
        for m in re.findall(r"verify_tenant_rls_release\.py --max-version (\d+)", source)
    }

    assert applied, "expected the workflow to cap apply_migrations"
    assert verified, (
        "verify_tenant_rls_release.py must be given the same --max-version the "
        "workflow migrates to, or a later migration fails the ledger check"
    )
    assert verified == {max(applied)}, (
        f"verify cap {verified} does not match the highest apply cap {max(applied)}"
    )


@pytest.mark.parametrize("bad", ["notamigration.sql", "abc_x.sql"])
def test_unparseable_migration_name_is_refused(bad: str):
    with pytest.raises(RuntimeError, match="invalid migration filename"):
        _migration_version(bad)
