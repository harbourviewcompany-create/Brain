# Validation Note

The repository now contains code, tests, fixtures, acceptance reports, GO/HOLD reports, traceability and CI validation configuration for issues #3-#8.

The required validation commands are:

```bash
python tools/validate_agent_control.py
pytest -q
ruff check .
```

These commands are wired into `.github/workflows/test.yml`.
