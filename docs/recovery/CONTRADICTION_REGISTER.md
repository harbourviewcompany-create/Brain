# Contradiction Register

| ID | Contradiction / risk | Severity | Current handling |
|---|---|---|---|
| CONTRA-001 | The word Brain refers to multiple object families | Critical | Split into Brain-Corpus, Brain-Registry, Brain-Beta, Brain-Manual, and Shared-Brain |
| CONTRA-002 | Shared-Brain could be mistaken for Brain-Corpus | High | Treat Shared-Brain as coordination only |
| CONTRA-003 | Brain-Beta could be mistaken for the full Brain system | High | Treat as fixture or demo until source is recovered |
| CONTRA-004 | Brain-Manual could be mistaken for implementation spec | High | Treat as reference until mapped |
| CONTRA-005 | Scope could be narrowed during synthesis | Critical | Extraction-first rule controls all future work |
| CONTRA-006 | Unclassified snippets could be copied into implementation | Critical | Do-not-copy default until contamination audit is recovered |
| CONTRA-007 | Function Registry update requested but registry unavailable | Critical | HOLD canonical registry updates |
| CONTRA-008 | Airtable project row exists but source artifacts are absent | High | Use Airtable only for project status and gates |
| CONTRA-009 | GitHub and Drive searches did not recover corpus artifacts | High | Mark source as missing or inaccessible until recovered |
| CONTRA-010 | Referenced artifacts are not available in this pass | Medium | Mark referenced/inaccessible, not recovered |
