from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import jwt
from jwt import PyJWKClient


VERCEL_JWKS_URL = "https://oidc.vercel.com/.well-known/jwks"


@dataclass(frozen=True, slots=True)
class VercelOidcConfig:
    team_slug: str
    project: str
    environment: str

    @classmethod
    def from_env(cls) -> "VercelOidcConfig":
        return cls(
            team_slug=os.environ.get("BRAIN_VERCEL_OIDC_TEAM_SLUG", "").strip(),
            project=os.environ.get("BRAIN_VERCEL_OIDC_PROJECT", "").strip(),
            environment=os.environ.get("BRAIN_VERCEL_OIDC_ENVIRONMENT", "").strip(),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.team_slug and self.project and self.environment)

    @property
    def audience(self) -> str:
        return f"https://vercel.com/{self.team_slug}"

    @property
    def subject(self) -> str:
        return (
            f"owner:{self.team_slug}:project:{self.project}:"
            f"environment:{self.environment}"
        )

    @property
    def allowed_issuers(self) -> frozenset[str]:
        return frozenset(
            {
                "https://oidc.vercel.com",
                f"https://oidc.vercel.com/{self.team_slug}",
            }
        )


class VercelOidcVerifier:
    """Verify Vercel deployment identity without sharing a static secret."""

    def __init__(
        self,
        config: VercelOidcConfig,
        *,
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        self.config = config
        self._jwks_client = jwks_client or PyJWKClient(VERCEL_JWKS_URL, cache_keys=True)

    @classmethod
    def from_env(cls) -> "VercelOidcVerifier":
        return cls(VercelOidcConfig.from_env())

    def verify(self, token: str) -> tuple[bool, str]:
        if not self.config.enabled:
            return False, "vercel_oidc_not_configured"
        if not token:
            return False, "vercel_oidc_token_missing"

        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                return False, "vercel_oidc_algorithm_rejected"

            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.config.audience,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
                leeway=30,
            )
        except jwt.PyJWTError:
            return False, "vercel_oidc_invalid_token"
        except Exception:
            # JWKS/network/provider failures must fail closed without leaking details.
            return False, "vercel_oidc_verification_unavailable"

        if payload.get("iss") not in self.config.allowed_issuers:
            return False, "vercel_oidc_issuer_rejected"
        if payload.get("sub") != self.config.subject:
            return False, "vercel_oidc_subject_rejected"

        return True, "vercel_oidc_verified"
