"""Migration version numbers must stay selectable.

`--max-version` and the CI baseline gate both pick migrations by the numeric
prefix, so two files sharing one version cannot be separated by either.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.apply_migrations import (
    GRANDFATHERED_DUPLICATE_VERSIONS,
    MIGRATIONS_DIR,
    _assert_unique_versions,
    _migration_version,
)


def test_repository_migrations_have_no_new_version_collisions():
    files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda path: path.name)
    assert files, "expected migrations on disk"
    _assert_unique_versions(files)


def test_a_new_duplicate_version_is_refused(tmp_path: Path):
    files = [tmp_path / "021_alpha.sql", tmp_path / "021_beta.sql"]
    with pytest.raises(RuntimeError, match="duplicate migration version"):
        _assert_unique_versions(files)


def test_grandfathered_collision_is_still_allowed(tmp_path: Path):
    # 006 shipped twice and both files are applied in production; renaming
    # either would orphan its brain_schema_migrations row.
    files = [tmp_path / "006_money_spine.sql", tmp_path / "006_working_memory.sql"]
    _assert_unique_versions(files)
    assert 6 in GRANDFATHERED_DUPLICATE_VERSIONS


def test_apply_order_is_total_even_within_a_shared_version():
    """Filename sort, not version number, decides order -- and it is stable."""
    names = sorted(p.name for p in MIGRATIONS_DIR.glob("006_*.sql"))
    assert names == ["006_money_spine.sql", "006_working_memory_predictions_learning.sql"]
    assert all(_migration_version(MIGRATIONS_DIR / name) == 6 for name in names)
