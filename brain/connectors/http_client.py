"""Shared HTTP client for connectors — stdlib only, strict limits."""

from __future__ import annotations

import gzip
import io
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping


DEFAULT_USER_AGENT = (
    "BrainIngest/1.0 (+https://github.com/harbourviewcompany-create/Brain; "
    "research-observation-bot; respectful-rate-limits)"
)
DEFAULT_MAX_BYTES = 2_000_000  # 2 MiB hard cap per response body


@dataclass(slots=True)
class HttpResponse:
    url: str
    status: int
    body: bytes
    headers: dict[str, str]
    duration_ms: float
    final_url: str


class HttpClientError(Exception):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class HttpClient:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        default_timeout: float = 20.0,
    ) -> None:
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self.default_timeout = default_timeout
        self._ctx = ssl.create_default_context()

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        if not url or not url.startswith(("http://", "https://")):
            raise HttpClientError(f"invalid_url:{url!r}")
        timeout = self.default_timeout if timeout is None else timeout
        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/rss+xml, application/atom+xml, application/json, application/xml, text/xml, text/html;q=0.8, */*;q=0.5",
            "Accept-Encoding": "gzip, identity",
        }
        if headers:
            req_headers.update({str(k): str(v) for k, v in headers.items()})
        request = urllib.request.Request(url, headers=req_headers, method="GET")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=self._ctx) as resp:
                status = int(getattr(resp, "status", 200) or 200)
                raw = resp.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raise HttpClientError("response_too_large", status=status)
                hdrs = {k.lower(): v for k, v in dict(resp.headers).items()}
                encoding = (hdrs.get("content-encoding") or "").lower()
                if encoding == "gzip":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(self.max_bytes + 1)
                    if len(raw) > self.max_bytes:
                        raise HttpClientError("response_too_large_after_gunzip", status=status)
                final_url = str(resp.geturl() or url)
                duration_ms = (time.perf_counter() - started) * 1000.0
                return HttpResponse(
                    url=url,
                    status=status,
                    body=raw,
                    headers=hdrs,
                    duration_ms=duration_ms,
                    final_url=final_url,
                )
        except urllib.error.HTTPError as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            try:
                exc.read(self.max_bytes)
            except Exception:
                pass
            raise HttpClientError(
                f"http_error:{exc.code}:{exc.reason}",
                status=int(exc.code),
            ) from exc
        except urllib.error.URLError as exc:
            raise HttpClientError(f"url_error:{exc.reason}") from exc
        except TimeoutError as exc:
            raise HttpClientError("timeout") from exc
