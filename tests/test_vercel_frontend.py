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


def test_vercel_headers_cache_at_the_edge_and_harden_the_static_page() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    headers = {
        entry["key"]: entry["value"]
        for entry in config["headers"][0]["headers"]
    }

    assert "s-maxage=300" in headers["Cache-Control"]
    assert "stale-while-revalidate" in headers["Cache-Control"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_index_html_has_favicon_and_social_preview_tags() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'rel="icon"' in html
    assert 'property="og:title"' in html
    assert 'name="twitter:card"' in html
