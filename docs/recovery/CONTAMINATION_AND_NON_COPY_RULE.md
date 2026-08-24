# Contamination and Non-Copy Rule

Current controlling rule:

Do not copy unsafe SQL/TypeScript snippets or treat uploaded implementation snippets as source code until they are classified.

Visible context indicates some SQL/TypeScript snippets were to be treated as contaminated reference and added as registry-only entries.

Since those snippets are not available in this pass, the safe default is:

| Artifact type | Default treatment |
|---|---|
| Uploaded SQL snippet | Do-not-copy |
| Uploaded TypeScript snippet | Do-not-copy |
| Route implementation snippet | Do-not-copy |
| RLS policy snippet | Do-not-copy |
| Dashboard code | Do-not-copy |
| Test snippet | Do-not-copy until classified |
| Registry-delta code | Registry-only until classified |
