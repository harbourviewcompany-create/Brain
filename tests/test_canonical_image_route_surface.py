"""The canonical API image must serve every route the Observatory calls.

`railway.toml` and both Docker CI jobs build `Dockerfile`, which runs
`apps.api.tenant_app` over `apps/api/main.py`. The cockpit read model used to
exist only in `tools/live_cockpit_routes.py`, served by `Dockerfile.railway` --
the image its own header calls the "Legacy Railway cockpit compatibility image".
So CI proved out an image the Observatory would 404 against, while the
deprecated one carried the read surface.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import TEST_API_KEY

client = TestClient(app, headers={"x-api-key": TEST_API_KEY})

REPO_ROOT = Path(__file__).resolve().parents[1]
API_CLIENT = REPO_ROOT / "apps" / "observatory" / "src" / "lib" / "api.ts"

#: Collection routes the Observatory client reads.
COCKPIT_READ_ROUTES = [
    "/signals",
    "/edges",
    "/contradictions",
    "/curiosity",
    "/sources",
    "/approvals",
    "/opportunities",
    "/outcomes",
    "/formula-runs",
    "/acceptance-reports",
]


@pytest.mark.parametrize("route", COCKPIT_READ_ROUTES)
def test_canonical_app_serves_cockpit_read_route(route: str):
    response = client.get(route)
    assert response.status_code == 200, f"{route} is missing from the canonical image"

    body = response.json()
    assert isinstance(body.get("items"), list)
    assert body.get("total") == len(body["items"])
    assert body.get("source") == "api"


@pytest.mark.parametrize("route", COCKPIT_READ_ROUTES)
def test_cockpit_read_routes_require_authentication(route: str):
    unauthenticated = TestClient(app)
    assert unauthenticated.get(route).status_code == 401


def test_every_route_the_observatory_client_calls_exists():
    """Catch a client function added against a route the API never gained."""
    source = API_CLIENT.read_text(encoding="utf-8")

    # request<T>("/beliefs") / requestOptional<T>(`/predictions/${id}`) ...
    called = set()
    for match in re.finditer(r"request(?:Optional)?<[^>]*>\(\s*[`\"']/([^`\"'$)]+)", source):
        path = "/" + match.group(1).rstrip("/")
        # Drop template-literal segments; only fixed collection paths are checked.
        if "${" in path:
            continue
        called.add(path)

    served = {
        route.path
        for route in app.routes
        if hasattr(route, "path") and "{" not in getattr(route, "path", "")
    }

    missing = sorted(path for path in called if path not in served)
    assert not missing, f"Observatory calls routes the canonical image does not serve: {missing}"
