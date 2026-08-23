# Brain Current Thread Archive

This folder is the repository control point for preserving the full current-thread Brain compilation package.

## Purpose

The current ZIP package contains the full compiled Brain thread, source pasted text, DOCX export, Markdown export, and six rendered visual artifacts. The repository currently has implementation scaffolding and summarized docs, but it does not yet contain the full archive payload.

This archive folder exists to make the missing package assets explicit, reproducible, and verifiable.

## Source package

Local package name:

```text
Brain_Compilation_Full_Current_Thread_Package.zip
```

Expected package SHA-256:

```text
5b17edc9e0bbc4d18b02bf83cae348c281ec5a84396e8f4eeb2fed53c5afb33c
```

Expected package size:

```text
18,545,024 bytes
```

## Required repository targets

The package should ultimately be preserved at these paths:

```text
docs/archive/Brain_Compilation_Full_Current_Thread.md
docs/archive/Brain_Compilation_Full_Current_Thread.docx
docs/archive/source/Pasted text.txt
docs/archive/visuals/step_by_step_process_overview.png
docs/archive/visuals/brain_functions_vs._real_brain_anatomy.png
docs/archive/visuals/a_high_detail_infographic_poster_on_a_dark_black_t.png
docs/archive/visuals/brain_vs_ai_a_comparative_overview.png
docs/archive/visuals/brain_architecture_vs_generic_ai_comparison.png
docs/archive/visuals/comparing_ai_and_brain_architectures.png
artifacts/Brain_Compilation_Full_Current_Thread_Package.zip
```

## Verification files

- `ARCHIVE_MANIFEST.md` records human-readable target paths, byte counts, and SHA-256 hashes.
- `archive_manifest.json` is the machine-readable registry used by the ingestion script.
- `scripts/ingest_current_thread_archive.py` verifies and extracts the package.

## Connector limitation

The GitHub connector available in this ChatGPT session can write literal UTF-8 text or base64 strings. It does not read local `/mnt/data/...` files as byte streams for file-parameter upload. For that reason, binary assets must be added through one of these methods:

1. Git command line from a local clone.
2. GitHub web upload.
3. A future file-byte-capable connector action.
4. A CI/artifact workflow that receives the package as a real file upload.

Do not commit placeholder files that only contain local paths.

## Correct ingestion flow

From a local clone of this repo:

```bash
python scripts/ingest_current_thread_archive.py /path/to/Brain_Compilation_Full_Current_Thread_Package.zip --repo-root .
```

Then review:

```bash
git status
git diff --stat
```

Then commit:

```bash
git add docs/archive artifacts
git commit -m "docs: add current thread archive package"
git push
```

## Rule

The archive is evidence preservation. It should not be rewritten, summarized, narrowed, or filtered. Newer compilations should be added as new archive versions, not overwrite this one.
