# PR #182 — Revenue Entity Extraction Repair Evidence

## Scope

Repair the review findings on `feat/revenue-entity-extraction` without merging, deploying, changing production configuration, or enabling live extraction.

## Enforced runtime properties

1. Model confidence is not evidence. An extracted field is accepted only when it includes a non-empty `evidence_quote` that is found in the bounded source observation after case/whitespace normalization.
2. Confidence must parse to a finite number in the closed interval `[0.0, 1.0]` before the configured threshold is considered.
3. Source/connector enrichment is authoritative. Model extraction only fills missing enrichment fields and cannot replace a non-empty source-provided field.
4. Accepted model fields retain `confidence`, verbatim `evidence_quote`, `model_id`, and `source_url` in `RevenueSignal.metadata.extraction_provenance`.
5. When an extracted signal becomes actionable, the same provenance is serialized into the approval action `evidence_refs` using the `extraction_provenance:` audit prefix so it survives normal action persistence without a schema change.
6. When an extracted signal remains non-actionable, its extraction provenance is included in the `revenue.signal_scored` audit event.
7. Extraction limits are scoped to public ingest operations: one scheduled `ingest_due_sources()` batch shares one budget, and each forced `ingest_source()` call receives a fresh budget.
8. The HTTP extraction prompt explicitly treats source content as untrusted data and requires a verbatim evidence quote. Prompt wording is defense in depth; deterministic source-quote validation remains authoritative.

## Added/updated regression coverage

- grounded extraction with matching quotes;
- unsupported/hallucinated model output rejection;
- prompt-injection source text that attempts to induce an unsupported buyer;
- non-finite, percentage-style, negative, and >1 confidence rejection;
- source-provided partial enrichment precedence;
- approval-action provenance retention;
- scheduled-operation budget reset;
- forced-ingest budget reset across repeated `ingest_source()` operations;
- local heuristic evidence-quote contract.

## Activation boundary

`BRAIN_REVENUE_EXTRACTION_ENABLED` remains explicit opt-in. This repair does not enable the feature, modify deploy configuration, call a live LLM provider, or perform any external revenue action.

Live provider cost/latency and labeled-real-feed extraction quality remain activation evidence to collect before enabling the flag in production; they are not replaced by unit/CI coverage.
