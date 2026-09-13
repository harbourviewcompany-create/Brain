"""SSRF and egress safety for brain.connectors.http_client."""

from __future__ import annotations

import ipaddress
from unittest.mock import patch

import pytest

from brain.connectors.http_client import (
    HttpClient,
    HttpClientError,
    assert_url_safe_for_egress,
    _is_public_ip,
)


@pytest.mark.parametrize(
    "ip,ok",
    [
        ("8.8.8.8", True),
        ("1.1.1.1", True),
        ("127.0.0.1", False),
        ("10.0.0.5", False),
        ("192.168.1.1", False),
        ("172.16.0.1", False),
        ("169.254.169.254", False),
        ("100.64.1.1", False),
        ("0.0.0.0", False),
        ("::1", False),
        ("fc00::1", False),
        ("fe80::1", False),
    ],
)
def test_is_public_ip(ip: str, ok: bool) -> None:
    assert _is_public_ip(ipaddress.ip_address(ip)) is ok


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://10.0.0.1/secret",
        "http://192.168.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "ftp://example.com/",
        "file:///etc/passwd",
        "https://localhost/admin",
    ],
)
def test_assert_url_blocks_non_public_and_bad_schemes(url: str) -> None:
    with pytest.raises(HttpClientError):
        assert_url_safe_for_egress(url)


def test_assert_url_blocks_dns_to_private_ip() -> None:
    """If DNS returns a private address, refuse before connect."""
    private_info = [
        (2, 1, 0, "", ("10.1.2.3", 443)),
    ]
    with patch("brain.connectors.http_client.socket.getaddrinfo", return_value=private_info):
        with pytest.raises(HttpClientError) as ei:
            assert_url_safe_for_egress("https://evil.example/feed.xml")
        assert "blocked_resolved_ip" in str(ei.value)


def test_client_get_rejects_loopback_without_network() -> None:
    client = HttpClient()
    with pytest.raises(HttpClientError):
        client.get("http://127.0.0.1:8080/")


def test_client_get_rejects_metadata_ip_without_network() -> None:
    client = HttpClient()
    with pytest.raises(HttpClientError):
        client.get("http://169.254.169.254/latest/meta-data/")
