from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_no_legacy_hosted_deployment_contracts():
    """The canonical production boundary must not contain deployable paid-host artifacts."""
    forbidden = (
        "fly.toml",
        "railway.toml",
        "railway.brain-api-live.toml",
        "railway.worker.toml",
        "Dockerfile.railway",
        "Dockerfile.worker",
    )
    present = [path for path in forbidden if (ROOT / path).exists()]
    assert not present, f"legacy hosted deployment artifacts present: {present}"
