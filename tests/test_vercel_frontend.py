from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_root_frontend_exists_and_identifies_brain() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "The Brain" in html
    assert "Revenue intelligence runtime" in html
    assert "Frontend route active" in html
    assert "external actions without approval" in html


def test_vercel_routes_all_paths_to_root_frontend() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert config["version"] == 2
    assert config["builds"] == [{"src": "index.html", "use": "@vercel/static"}]
    assert {"src": "/(.*)", "dest": "/index.html"} in config["routes"]
