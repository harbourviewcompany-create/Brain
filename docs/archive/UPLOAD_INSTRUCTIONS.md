# Upload Instructions for Current Thread Archive Assets

The archive manifest and ingestion script are committed to this branch. The actual ZIP/DOCX/PNG assets still need a file-byte-capable upload path.

## Preferred local Git flow

From a local machine:

```bash
git clone https://github.com/harbourviewcompany-create/Brain.git
cd Brain
git fetch origin archive/current-thread-package
git checkout archive/current-thread-package
python scripts/ingest_current_thread_archive.py /path/to/Brain_Compilation_Full_Current_Thread_Package.zip --repo-root .
git status
git diff --stat
git add docs/archive artifacts
git commit -m "docs: add current thread archive assets"
git push origin archive/current-thread-package
```

Then return to PR #1 and verify that the following files are present:

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

## GitHub web upload fallback

If using GitHub web upload, upload files to the exact target paths listed in `docs/archive/archive_manifest.json`.

After upload, verify each file size and SHA-256 locally against the manifest. Do not rename files unless the manifest is updated in the same commit.

## Do not do this

Do not create files that contain only local paths such as:

```text
/mnt/data/Brain_Compilation_Full_Current_Thread.md
```

That is a placeholder, not the archive.

## Why this exists

The archive is the evidence-preservation layer for the Brain work from this thread. It should remain raw, complete, and separately versioned from implementation summaries.
