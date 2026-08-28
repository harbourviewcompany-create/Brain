"""Worker revenue-extraction configuration must never block cognition startup."""

from __future__ import annotations

import importlib


worker = importlib.import_module("apps.worker.main")


def test_extraction_batch_limit_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("BRAIN_REVENUE_EXTRACTION_BATCH_LIMIT", raising=False)
    assert worker.revenue_extraction_batch_limit() == 20


def test_extraction_batch_limit_defaults_when_empty(monkeypatch):
    monkeypatch.setenv("BRAIN_REVENUE_EXTRACTION_BATCH_LIMIT", "   ")
    assert worker.revenue_extraction_batch_limit() == 20


def test_extraction_batch_limit_defaults_when_non_numeric(monkeypatch):
    monkeypatch.setenv("BRAIN_REVENUE_EXTRACTION_BATCH_LIMIT", "not-a-number")
    assert worker.revenue_extraction_batch_limit() == 20


def test_extraction_batch_limit_defaults_when_negative(monkeypatch):
    monkeypatch.setenv("BRAIN_REVENUE_EXTRACTION_BATCH_LIMIT", "-1")
    assert worker.revenue_extraction_batch_limit() == 20


def test_extraction_batch_limit_preserves_zero_and_positive_values(monkeypatch):
    monkeypatch.setenv("BRAIN_REVENUE_EXTRACTION_BATCH_LIMIT", "0")
    assert worker.revenue_extraction_batch_limit() == 0
    monkeypatch.setenv("BRAIN_REVENUE_EXTRACTION_BATCH_LIMIT", "7")
    assert worker.revenue_extraction_batch_limit() == 7
