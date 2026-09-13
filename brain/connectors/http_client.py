"""Shared HTTP client for connectors — stdlib only, strict limits + SSRF guards."""

from __future__ import annotations

import gzip
import io
import ipaddress
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Mapping


DEFAULT_USER_AGENT = (
    "BrainIngest/1.0 (+https://github.com/harbourviewcompany-create/Brain; "
    "research-observation-bot; respectful-rate-limits)"
)
DEFAULT_MAX_BYTES = 2_000_000  # 2 MiB hard cap per response body
DEFAULT_MAX_REDIRECTS = 5

# Hostnames that must never be contacted by automated ingest.
_BLOCKED_HOSTNAMES = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
        "kubernetes.default",
        "kubernetes.default.svc",
    }
)


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


def _is_public_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True only for globally routable addresses safe for egress fetches."""
    if addr.is_private or addr.is_loopback or addr.is_link_local:
        return False
    if addr.is_multicast or addr.is_reserved or addr.is_unspecified:
        return False
    # CGNAT / shared address space (RFC 6598)
    if isinstance(addr, ipaddress.IPv4Address) and addr in ipaddress.ip_network("100.64.0.0/10"):
        return False
    return True


def assert_url_safe_for_egress(url: str) -> urllib.parse.ParseResult:
    """Validate scheme + host + resolved addresses before any socket connect.

    Raises HttpClientError when the URL targets a non-public network location.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as exc:  # noqa: BLE001 — treat any parse failure as unsafe
        raise HttpClientError(f"invalid_url:{url!r}") from exc

    if parsed.scheme not in {"http", "https"}:
        raise HttpClientError(f"invalid_url_scheme:{parsed.scheme!r}")
    host = (parsed.hostname or "").strip().rstrip(".").lower()
    if not host:
        raise HttpClientError(f"invalid_url_host:{url!r}")
    if host in _BLOCKED_HOSTNAMES:
        raise HttpClientError(f"blocked_hostname:{host}")

    # Literal IP in the URL — check without DNS.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not _is_public_ip(literal):
            raise HttpClientError(f"blocked_literal_ip:{host}")
        return parsed

    # DNS resolution — reject if *any* address is non-public (DNS rebinding hygiene).
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HttpClientError(f"dns_error:{host}:{exc}") from exc
    if not infos:
        raise HttpClientError(f"dns_empty:{host}")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError as exc:
            raise HttpClientError(f"dns_bad_addr:{ip_str}") from exc
        if not _is_public_ip(addr):
            raise HttpClientError(f"blocked_resolved_ip:{host}->{ip_str}")

    return parsed


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Disable urllib's automatic redirects so each hop can be re-validated."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class HttpClient:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        default_timeout: float = 20.0,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
    ) -> None:
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self.default_timeout = default_timeout
        self.max_redirects = max(0, int(max_redirects))
        self._ctx = ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            _NoRedirect(),
            urllib.request.HTTPSHandler(context=self._ctx),
        )

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        timeout = self.default_timeout if timeout is None else timeout
        started = time.perf_counter()
        current = url
        pending_headers = {
            "User-Agent": self.user_agent,
            "Accept": (
                "application/rss+xml, application/atom+xml, application/json, "
                "application/xml, text/xml, text/html;q=0.8, */*;q=0.5"
            ),
            "Accept-Encoding": "gzip, identity",
        }
        if headers:
            pending_headers.update({str(k): str(v) for k, v in headers.items()})

        for _hop in range(self.max_redirects + 1):
            assert_url_safe_for_egress(current)
            request = urllib.request.Request(current, headers=pending_headers, method="GET")
            try:
                with self._opener.open(request, timeout=timeout) as resp:
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
                    final_url = str(resp.geturl() or current)
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
                # 3xx with NoRedirect handler surfaces as HTTPError.
                if exc.code in {301, 302, 303, 307, 308}:
                    location = exc.headers.get("Location") if exc.headers else None
                    try:
                        exc.read(self.max_bytes)
                    except Exception:
                        pass
                    if not location:
                        raise HttpClientError(
                            f"redirect_without_location:{exc.code}",
                            status=int(exc.code),
                        ) from exc
                    current = urllib.parse.urljoin(current, location)
                    continue
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

        raise HttpClientError(f"too_many_redirects:{self.max_redirects}")
