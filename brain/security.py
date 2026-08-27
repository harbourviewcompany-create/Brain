from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Mapping

#: Every header a caller may present a Brain credential in. All of them are
#: checked; none of them takes precedence over the others.
CREDENTIAL_HEADERS = ("x-brain-api-key", "x-api-key", "authorization")


def credential_candidates(headers: Mapping[str, str]) -> list[str]:
    """Return every credential a request presents, in no particular order.

    A caller can legitimately present more than one credential at once -- the
    Observatory BFF, for example, may carry both a platform identity token in
    ``authorization`` and the Brain API key in ``X-Brain-Api-Key``. Treating any
    single header as authoritative means an unrelated bearer token silently
    masks a valid API key, so every presented value is collected and the caller
    is authorized if *any* of them matches.
    """

    normalized = {key.lower(): value for key, value in headers.items()}
    candidates: list[str] = []
    for header in CREDENTIAL_HEADERS:
        raw = (normalized.get(header) or "").strip()
        if not raw:
            continue
        if header == "authorization":
            if raw.lower().startswith("bearer "):
                raw = raw[7:].strip()
            else:
                continue
        if raw:
            candidates.append(raw)
    return candidates


def presented_credentials(headers: Mapping[str, str], expected: str) -> bool:
    """Return true when any credential the request presents matches ``expected``."""

    if not expected:
        return False
    return any(
        hmac.compare_digest(candidate, expected)
        for candidate in credential_candidates(headers)
    )


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    environment: str
    api_key: str | None
    cors_origins: tuple[str, ...]
    external_actions_enabled: bool

    @property
    def production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        environment = os.environ.get("BRAIN_ENV", "development")
        key = os.environ.get("BRAIN_API_KEY") or None
        raw_origins = os.environ.get("BRAIN_CORS_ORIGINS", "")
        origins = tuple(item.strip() for item in raw_origins.split(",") if item.strip())
        external = os.environ.get("BRAIN_EXTERNAL_ACTIONS_ENABLED", "false").lower() == "true"
        config = cls(environment, key, origins, external)
        config.validate()
        return config

    def validate(self) -> None:
        if self.production and not self.api_key:
            raise RuntimeError("BRAIN_API_KEY is required in production")
        if self.production and self.external_actions_enabled:
            approval_mode = os.environ.get("BRAIN_EXTERNAL_ACTION_APPROVAL_MODE", "")
            if approval_mode != "explicit":
                raise RuntimeError(
                    "production external actions require BRAIN_EXTERNAL_ACTION_APPROVAL_MODE=explicit"
                )

    def allowed_origins(self) -> list[str]:
        if self.production:
            return list(self.cors_origins)
        return list(self.cors_origins) or ["*"]


class ApiKeyAuthenticator:
    def __init__(self, config: SecurityConfig) -> None:
        self.config = config

    def authorized(self, *, authorization: str | None, x_api_key: str | None) -> bool:
        expected = self.config.api_key
        if not expected:
            return not self.config.production
        headers = {
            "authorization": authorization or "",
            "x-api-key": x_api_key or "",
        }
        return presented_credentials(headers, expected)

    @staticmethod
    def fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
