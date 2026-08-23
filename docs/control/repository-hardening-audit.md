# Repository Hardening Audit

Status: APPROVED control enforcement support.

This audit exists because two important gaps cannot be fully closed by ordinary repository file commits in the current execution environment:

1. GitHub branch protection / repository ruleset configuration for `main`.
2. Upload of the real archive DOCX, Markdown, source text, PNG, and ZIP file bytes.

The audit does not mutate GitHub settings, upload files, or create placeholders. It detects whether the gaps still exist and points to the controlling issues.

## Required branch protection state

`main` must require these checks before merge:

```text
Brain Control Policy
test
```

Recommended branch controls:

```text
Require pull request before merge
Require branches to be up to date before merging
Block force pushes
Block branch deletions
Require conversation resolution when available
```

A candidate ruleset is stored at:

```text
.github/rulesets/main-required-checks.ruleset.json
```

That file is a configuration target for a GitHub admin, a ruleset-capable tool, or an external settings automation. It is not automatically applied by GitHub just because it exists in the repo.

## Required archive state

The archive manifest expects the real file bytes at the paths listed in `docs/archive/archive_manifest.json`, including the DOCX, Markdown, pasted source text, six PNG files, and ZIP package.

Do not satisfy this with placeholder files or local path strings. The archive upload is complete only when:

```bash
python scripts/validate_archive_manifest.py
```

verifies present assets against the manifest byte counts and SHA-256 values.

## Audit command

```bash
GITHUB_TOKEN=<token> GITHUB_REPOSITORY=harbourviewcompany-create/Brain python scripts/check_repository_hardening.py
```

The corresponding workflow is:

```text
.github/workflows/repository-hardening.yml
```

It runs on `workflow_dispatch` and a daily schedule.

## Expected blocked state before manual completion

The audit is expected to fail until both blocked gaps are closed:

```text
Issue #51: branch protection / ruleset configuration
Issue #52: real archive file-byte upload
```

## GO/HOLD

GO for using this audit to verify hardening state.

HOLD for claiming repository hardening is complete until the audit passes and the branch metadata reports `main` as protected with the required checks.

## Source Preservation Statement

This audit preserves unresolved gaps explicitly. It does not narrow The Brain, reinterpret source material, delete archive requirements, or create fake completion evidence.
