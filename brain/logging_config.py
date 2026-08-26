"""Structured logging for the Brain runtime.

Before this module the repository imported `logging` in exactly one file, and
the cognition loop carried dozens of `except Exception: pass` handlers. A
self-modifying runtime that degrades silently cannot be diagnosed from a
running system, so the loop now reports what failed while still refusing to let
one failing organ stop cognition.

Output is JSON when BRAIN_LOG_FORMAT=json (the default in production), and
human-readable otherwise. Configuration is idempotent and never attaches a
second handler.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

_CONFIGURED = False

#: Keys LogRecord always carries. Anything else came from `extra=` and is
#: promoted into the structured payload.
_STANDARD_RECORD_KEYS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "stacklevel", "thread", "threadName",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, so log aggregators can index the fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_KEYS or key.startswith("_"):
                continue
            payload[key] = value if _json_safe(value) else repr(value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def _json_safe(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, type(None), list, dict))


def configure_logging(*, force: bool = False) -> None:
    """Attach a single stderr handler to the `brain` logger tree.

    Safe to call from any entrypoint and safe to call repeatedly. Uses its own
    logger rather than the root so importing the Brain never hijacks logging for
    an embedding application.
    """

    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    level_name = (os.environ.get("BRAIN_LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    use_json = (os.environ.get("BRAIN_LOG_FORMAT") or "json").strip().lower() == "json"
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        JsonFormatter()
        if use_json
        else logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )

    root = logging.getLogger("brain")
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
    # Off by default so an application that has already configured the root
    # logger does not get every Brain record twice. Set BRAIN_LOG_PROPAGATE=true
    # to forward records to root as well -- which is what lets pytest's caplog,
    # and any root-level aggregator, observe them.
    root.propagate = (os.environ.get("BRAIN_LOG_PROPAGATE") or "").strip().lower() == "true"

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger under the `brain` tree."""

    configure_logging()
    suffix = name.removeprefix("brain.").removeprefix("apps.")
    return logging.getLogger(f"brain.{suffix}")
