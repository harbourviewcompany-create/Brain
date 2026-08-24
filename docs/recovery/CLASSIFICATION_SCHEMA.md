# Required Classification Schema

Every recovered artifact should be classified before it is used.

| Field | Allowed values / purpose |
|---|---|
| source_id | Stable ledger ID |
| artifact_name | Exact filename/title |
| object_family | Brain-Corpus, Brain-Registry, Brain-Beta, Brain-Manual, Shared-Brain |
| source_type | chat, doc, markdown, code, SQL, TypeScript, repo, package, test log, manual, Notion, Linear, Airtable |
| authority_level | canonical, reference, contaminated, duplicate, missing, inaccessible |
| copy_permission | copy-allowed, transform-only, cite-only, registry-only, do-not-copy |
| implementation_permission | implementation-allowed, hold, deprecated, unsafe |
| evidence_status | verified, unverified, partial, unavailable |
| dependency | Upstream artifact required before use |
| decision_required | yes/no |
| notes | Exact reason for classification |
