"""Every API host path must build an image that can actually serve production.

`railway.toml` named `Dockerfile` as the canonical API deployment, but that
image copied only `brain`, `apps` and `db`. Two things followed from the missing
`tools`:

* the image had no `VercelOidcAuthBridge`, so the Vercel BFF's
  `Authorization: Bearer <OIDC token>` -- the entire documented production auth
  path -- reached an app that knows nothing about it; and
* `python tools/apply_migrations.py` could not run there, so the canonical
  config carried no `preDeployCommand` and a deploy driven by it applied no
  migrations, while the sibling `railway.brain-api-live.toml` did.

The two configs therefore deployed materially different systems, and the one the
repository called canonical was the one that could not serve.

Fly is held to the same invariants: same Dockerfile, bridged entrypoint, `/ready`,
and a release/migrate step capped at the pre-tenant ceiling.
"""

from __future__ import annotations

import re
import shlex
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The ASGI target every API entrypoint must run. It is
#: apps.api.tenant_app's own app object wrapped in the OIDC bridge -- not a
#: second application -- which is what test_railway_api_entrypoint_is_the_bridged_tenant_app proves.
API_ENTRYPOINT = "tools.live_cockpit_routes:app"
WORKER_ENTRYPOINT = "apps.worker.main"

#: The one image every API host builds, and the one path they all probe. Pinned
#: rather than read back from railway.toml: deriving "canonical" from one of the
#: files under test lets the invariant move silently when both are edited
#: together, which is the exact drift this module exists to catch.
API_DOCKERFILE = "Dockerfile"
API_HEALTHCHECK_PATH = "/ready"

#: Production pre-tenant migration ceiling (#170). Railway brain-api-live and Fly
#: release_command must not attempt gated tenant migrations 019+ on ordinary deploys.
PRETENANT_MAX_VERSION = "18"


def _dockerfile_copies(dockerfile: Path) -> set[str]:
    """Top-level source trees the image copies in, e.g. {"brain", "apps", "tools"}."""
    copied: set[str] = set()
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("COPY "):
            continue
        parts = shlex.split(stripped[len("COPY ") :])
        # The final argument is the destination; everything before it is a source.
        for source in parts[:-1]:
            if source.startswith("--"):
                continue
            copied.add(source.strip("./").split("/")[0])
    return copied


def _dockerfile_cmd(dockerfile: Path) -> str:
    match = re.search(
        r"^CMD\s+(.+)$", dockerfile.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert match, f"{dockerfile.name} declares no CMD"
    return match.group(1)


def _railway_configs() -> list[Path]:
    configs = sorted(REPO_ROOT.glob("railway*.toml"))
    assert configs, "expected Railway deployment configs at the repository root"
    return configs


def _load(config: Path) -> dict:
    return tomllib.loads(config.read_text(encoding="utf-8"))


def _load_fly() -> dict:
    return tomllib.loads((REPO_ROOT / "fly.toml").read_text(encoding="utf-8"))


API_CONFIGS = [p for p in _railway_configs() if "worker" not in p.name]


def test_every_railway_config_names_a_dockerfile_that_exists():
    for config in _railway_configs():
        path = _load(config)["build"]["dockerfilePath"]
        assert (REPO_ROOT / path).is_file(), f"{config.name} names a missing {path}"


@pytest.mark.parametrize("config", API_CONFIGS, ids=lambda p: p.name)
def test_api_configs_all_build_one_image_and_probe_one_path(config: Path):
    """Two API configs that disagree deploy two different systems."""
    settings = _load(config)

    assert settings["build"]["dockerfilePath"] == API_DOCKERFILE
    assert settings["deploy"]["healthcheckPath"] == API_HEALTHCHECK_PATH, (
        "/health answers before the database is reachable, so a Railway deploy "
        "probing it can go live over a broken runtime"
    )


@pytest.mark.parametrize("config", API_CONFIGS, ids=lambda p: p.name)
def test_api_configs_apply_migrations_on_deploy(config: Path):
    command = _load(config)["deploy"]["preDeployCommand"]
    assert any("apply_migrations.py" in part for part in command), (
        f"{config.name} deploys without applying migrations"
    )


def test_brain_api_live_caps_migrations_at_pretenant_ceiling():
    command = " ".join(_load(REPO_ROOT / "railway.brain-api-live.toml")["deploy"]["preDeployCommand"])
    assert f"--max-version {PRETENANT_MAX_VERSION}" in command


@pytest.mark.parametrize("config", _railway_configs(), ids=lambda p: p.name)
def test_predeploy_scripts_exist_in_the_image_they_run_in(config: Path):
    """The original defect: a command naming a tree the Dockerfile never copied."""
    settings = _load(config)
    command = settings["deploy"].get("preDeployCommand")
    if not command:
        return

    dockerfile = REPO_ROOT / settings["build"]["dockerfilePath"]
    copied = _dockerfile_copies(dockerfile)

    for part in command:
        for token in shlex.split(part):
            if not token.endswith(".py"):
                continue
            assert (REPO_ROOT / token).is_file(), f"{token} is not in the repository"
            tree = token.split("/")[0]
            assert tree in copied, (
                f"{config.name} runs {token}, but {dockerfile.name} never "
                f"COPYs {tree}/ -- the command cannot resolve inside the image"
            )


def test_api_images_serve_the_bridged_entrypoint():
    for dockerfile in {
        REPO_ROOT / _load(config)["build"]["dockerfilePath"] for config in API_CONFIGS
    } | {REPO_ROOT / "Dockerfile.railway"}:
        assert API_ENTRYPOINT in _dockerfile_cmd(dockerfile), (
            f"{dockerfile.name} runs an entrypoint without the Vercel OIDC bridge"
        )


def test_api_images_carry_the_tools_tree():
    for dockerfile in {
        REPO_ROOT / _load(config)["build"]["dockerfilePath"] for config in API_CONFIGS
    } | {REPO_ROOT / "Dockerfile.railway"}:
        assert "tools" in _dockerfile_copies(dockerfile), (
            f"{dockerfile.name} runs {API_ENTRYPOINT} but does not COPY tools/"
        )


def test_railway_api_entrypoint_is_the_bridged_tenant_app():
    """The bridge must wrap the canonical app, not stand up a second one.

    If these ever diverged, the Railway image would serve a different route
    surface, tenant boundary and RLS posture than every test in this suite.
    """
    import apps.api.tenant_app as tenant_app
    from tools.live_cockpit_routes import VercelOidcAuthBridge
    from tools.live_cockpit_routes import app as railway_app

    assert isinstance(railway_app, VercelOidcAuthBridge)
    assert railway_app.inner_app is tenant_app.app


def test_fly_runs_the_same_entrypoint_as_railway():
    """Fly declared its own process command, so it silently bypassed the bridge.

    `[processes] app` overrides the image CMD. It named `apps.api.main:app`,
    which is the bare FastAPI object -- no tenant membership/RLS wrapper from
    apps.api.tenant_app and no Vercel OIDC bridge.
    """
    fly = _load_fly()
    assert fly["build"]["dockerfile"] == API_DOCKERFILE
    assert API_ENTRYPOINT in fly["processes"]["app"]
    assert WORKER_ENTRYPOINT in fly["processes"]["worker"]

    # Fly declares its own health check too. Left unasserted, Fly could probe
    # /health while every Railway path probes /ready -- the same split this
    # module closed between the two Railway configs.
    checks = fly["http_service"]["checks"]
    assert [check["path"] for check in checks] == [API_HEALTHCHECK_PATH] * len(checks)
    assert fly["http_service"]["processes"] == ["app"], (
        "the worker exposes no HTTP port; attaching it to the service would "
        "route traffic at a process that cannot answer"
    )


def test_fly_applies_pretenant_migrations_on_release():
    """Ordinary Fly deploys must not run gated tenant migrations 019+."""
    fly = _load_fly()
    release = fly["deploy"]["release_command"]
    assert "apply_migrations.py" in release
    assert f"--max-version {PRETENANT_MAX_VERSION}" in release
    # release_command runs inside the built image; tools/ must be present.
    assert "tools" in _dockerfile_copies(REPO_ROOT / API_DOCKERFILE)


def test_fly_worker_is_not_on_the_http_service():
    fly = _load_fly()
    assert "worker" in fly["processes"]
    assert "worker" not in fly["http_service"]["processes"]


def test_worker_config_targets_the_worker_image():
    settings = _load(REPO_ROOT / "railway.worker.toml")
    dockerfile = REPO_ROOT / settings["build"]["dockerfilePath"]
    assert WORKER_ENTRYPOINT in _dockerfile_cmd(dockerfile)
    assert "deploy" in settings and "healthcheckPath" not in settings["deploy"], (
        "a background worker exposes no HTTP port to probe"
    )
