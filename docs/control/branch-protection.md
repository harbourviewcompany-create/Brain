# Branch Protection Requirements

## Purpose

This document defines the repository branch-protection settings required to make the Brain control layer enforceable instead of advisory.

The control layer can validate files in CI, but GitHub must be configured to require those checks before merging to `main`.

## Required Branch

```text
main
```

## Required Status Checks

Require these checks before merge:

```text
Brain Control Policy / Validate Brain control policy
test / test
```

If GitHub displays status-check names differently, select the checks produced by:

```text
.github/workflows/control-policy.yml
.github/workflows/test.yml
```

## Required Protection Settings

Enable:

```text
Require a pull request before merging
Require status checks to pass before merging
Require branches to be up to date before merging
Require conversation resolution before merging
Do not allow bypassing the above settings
```

Recommended:

```text
Require approvals: 1
Dismiss stale approvals when new commits are pushed
Require review from Code Owners once CODEOWNERS exists
Restrict force pushes
Prevent deletion of the branch
```

## Manual Configuration Path

Repository settings path:

```text
Settings -> Branches -> Branch protection rules -> Add branch ruleset or Add rule
```

Target branch pattern:

```text
main
```

## Governance Rule

Do not merge Brain implementation work unless:

```text
Control policy passed: yes
General test workflow passed: yes
PR body contains acceptance evidence: yes
Traceability records updated for changed code: yes
External actions disclosed: yes/no
Memory writes disclosed: yes/no
Source preservation statement present: yes
```

## Current Limitation

This document does not configure branch protection by itself. It records the required protection policy. Actual repository settings must be applied through GitHub settings, repository rulesets, or a future approved GitHub administration automation.
