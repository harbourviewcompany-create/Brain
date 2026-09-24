from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBSERVATORY = ROOT / "apps" / "observatory"
PRODUCTION_WIRING = ROOT / "docs" / "observatory" / "PRODUCTION_WIRING.md"


def test_root_vercel_config_is_deployment_control_not_frontend_authority() -> None:
    assert not (ROOT / "index.html").exists()
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rules = config["git"]["deploymentEnabled"]
    assert rules["**"] is False
    assert rules["main"] is True
    assert rules["preview/*"] is True
    assert config["ignoreCommand"] == "bash scripts/vercel-ignore-build.sh"


def test_observatory_is_the_canonical_nextjs_vercel_app() -> None:
    package = json.loads((OBSERVATORY / "package.json").read_text(encoding="utf-8"))
    config = json.loads((OBSERVATORY / "vercel.json").read_text(encoding="utf-8"))

    assert package["name"] == "brain-observatory"
    assert package["scripts"]["build"] == "next build"
    assert config["framework"] == "nextjs"
    assert config["buildCommand"] == "npm run build"
    assert config["outputDirectory"] == ".next"
    assert config["git"]["deploymentEnabled"]["**"] is False
    assert config["git"]["deploymentEnabled"]["main"] is True
    assert config["ignoreCommand"] == "bash ../../scripts/vercel-ignore-build.sh"


def test_production_wiring_names_canonical_frontend_and_api() -> None:
    wiring = PRODUCTION_WIRING.read_text(encoding="utf-8")

    assert "Vercel (`api/index.py`) + **Turso/libSQL**" in wiring
    assert "Railway **or** Fly" not in wiring
    assert "BRAIN_API_URL=<active API host HTTPS origin>" not in wiring
    assert "harbourviewcompany-create/Brain" in wiring
    assert "apps/observatory" in wiring


def test_observatory_readme_matches_live_production_wiring() -> None:
    readme = (OBSERVATORY / "README.md").read_text(encoding="utf-8")

    assert "Vercel project: `brain`" in readme
    assert "Canonical production URL" in readme
    assert "Root Directory `apps/observatory`" not in readme
    assert "Railway" not in readme
    assert "Fly" not in readme
    assert "project currently builds from the repository root" not in readme
