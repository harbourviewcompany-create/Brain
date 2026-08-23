# Conformance Reports

This directory is reserved for evidence generated under `docs/control/MOD_008_015_CONFORMANCE_AUDIT_PROTOCOL.md`.

Governing audit issue: #34.

Required MOD-008 through MOD-015 outputs:

- `MOD-008-015-conformance.json` — complete atomic requirement matrix.
- `MOD-008-015-conformance.md` — operator-readable matrix and module summaries.
- `MOD-008-015-gap-register.json` — every mandatory non-PASS row, mapped to an owner issue and repair target.

A report must pin the exact audited commit SHA. Reports from an older commit cannot establish GO for a newer head. Aggregate CI success cannot substitute for missing atomic evidence.
