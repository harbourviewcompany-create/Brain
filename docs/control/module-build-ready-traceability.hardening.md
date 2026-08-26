# Runtime hardening module BUILD-READY traceability extension

Covers the modules added by the runtime hardening pass that closed the repository
review findings. Each row is backed by an executable regression test, not by review
alone. Rows stay HOLD, as every other canonical matrix row does: BUILD-READY is
reserved until all evidence is present. The source record is [`RUNTIME_HARDENING_REVIEW.md`](RUNTIME_HARDENING_REVIEW.md).

| Module | owner object | schema | runtime service | state machine | fixtures | tests | acceptance criteria | audit events | GO/HOLD status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `apps/api/cockpit_read_routes.py` | Brain cockpit read model | `{items, total, source}` list envelope | canonical FastAPI app in `apps.api.main` | durable event stream and belief store -> read projection -> authenticated JSON | `tests/test_canonical_image_route_surface.py`; `tests/test_live_cockpit_signals.py` | `pytest tests/test_canonical_image_route_surface.py` | canonical image serves every route the Observatory calls; all require auth | COCKPIT_READ_MODEL_SERVED | HOLD |
| `brain/logging_config.py` | Brain runtime observability | one JSON object per line: ts, level, logger, message, extras, traceback | `brain.logging_config`, configured by every entrypoint | unconfigured -> single stderr handler on the `brain` tree -> namespaced loggers | `tests/test_worker_persistence.py` | `pytest tests/test_worker_persistence.py` | idempotent configuration; root logger untouched; cognition loop reports every swallowed failure | COGNITION_STEP_FAILED | HOLD |
