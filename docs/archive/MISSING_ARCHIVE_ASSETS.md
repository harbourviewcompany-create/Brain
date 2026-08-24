# Missing Archive Assets

Status: preservation blocker.

`docs/archive/ARCHIVE_MANIFEST.md` lists archive assets that are not present as committed repository blobs. The manifest must not be treated as a substitute for the actual source files.

The expected byte counts and SHA-256 values are recorded in `docs/archive/ARCHIVE_MANIFEST.md` and should be used when the assets are later committed.

Preservation status is HOLD until the missing assets are committed or explicitly superseded by a new source-preservation decision.

Runtime implementation remains unaffected by this file. Agents must not claim the repository fully preserves the current-thread archive until the archive manifest is resolved.
