"""Shared pytest configuration.

Sets a fixed BRAIN_API_KEY for the test session so that apps/api/main.py's
fail-closed API-key middleware doesn't reject every request made by
TestClient-based tests. This key is a test fixture, not a real secret, and
is never read from or written to any deployment environment.
"""
import os

TEST_API_KEY = "test-brain-api-key-not-a-secret"

os.environ.setdefault("BRAIN_API_KEY", TEST_API_KEY)
