from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass


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
        candidate = x_api_key or ""
        if authorization and authorization.lower().startswith("bearer "):
            candidate = authorization[7:].strip()
        return bool(candidate) and hmac.compare_digest(candidate, expected)

    @staticmethod
    def fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
