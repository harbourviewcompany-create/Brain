# PR #182 — Revenue Entity Extraction Repair Evidence

## Scope

Repair the review findings on `feat/revenue-entity-extraction` without merging, deploying, changing production configuration, or enabling live extraction.

## Enforced runtime properties

1. Model confidence is not evidence. An extracted field is accepted only when it includes a non-empty `evidence_quote` found in the bounded source observation after case/whitespace normalization.
2. The normalized extracted `value` must itself occur inside that supporting quote. A model cannot pair an invented value with an unrelated real quote to satisfy the grounding gate.
3. Confidence must be an actual JSON numeric value, not a boolean, and must be finite in the closed interval `[0.0, 1.0]` before the configured threshold is considered. Python's `bool`-as-`int` coercion is explicitly rejected.
4. Source/connector enrichment is authoritative. Model extraction only fills missing enrichment fields and cannot replace a non-empty source-provided field.
5. Accepted model fields retain `confidence`, verbatim `evidence_quote`, `model_id`, and `source_url` in `RevenueSignal.metadata.extraction_provenance`.
6. When an extracted signal becomes actionable, the provenance is appended to the packaged offer before `queue_action_from_scored`, so the approval action's first persisted `evidence_refs` insert already contains the `extraction_provenance:` audit record.
7. When an extracted signal remains non-actionable, its extraction provenance is included in the `revenue.signal_scored` audit event.
8. Extraction limits are scoped to public ingest operations: one scheduled `ingest_due_sources()` batch shares one call-count budget, and each forced `ingest_source()` call receives a fresh count budget.
9. Optional extraction also has an operation-wide monotonic wall-clock budget. The default is 10 seconds for the full scheduled or forced ingest operation, independent of the configured maximum number of extraction calls.
10. Before each model-backed extraction, `IngestService` computes the remaining operation budget. Once the deadline is exhausted, later extraction attempts are skipped and cognition can continue.
11. The remaining operation budget is propagated through `ReasonRequest.timeout_seconds`; `HttpLLMReasoner` caps the network timeout to the smaller of that remaining budget and its normal configured timeout, preventing serial calls from multiplying a 30-second provider timeout across a batch.
12. `BRAIN_REVENUE_EXTRACTION_BATCH_LIMIT` is fail-soft configuration: unset/empty/malformed/negative values fall back to the bounded default; valid zero remains an explicit zero-call budget. Extraction-only configuration cannot prevent the cognition worker from starting.
13. The HTTP extraction prompt explicitly treats source content as untrusted data and requires a verbatim evidence quote. Prompt wording is defense in depth; deterministic source/value/quote validation remains authoritative.

## Added/updated regression coverage

- grounded extraction with matching quotes;
- unsupported/hallucinated model output rejection;
- invented value paired with an unrelated real quote rejection;
- prompt-injection source text that attempts to induce an unsupported buyer;
- non-finite, percentage-style, negative, and >1 confidence rejection;
- JSON boolean confidence rejection for both `true` and `false`;
- source-provided partial enrichment precedence;
- approval-action provenance retention on the initial persisted action;
- scheduled-operation count-budget reset;
- forced-ingest count-budget reset across repeated `ingest_source()` operations;
- operation-wide wall-clock deadline enforcement, including skipping later extraction after expiry;
- remaining-deadline propagation from ingest into the extraction request;
- direct HTTP reasoner verification that `urlopen()` receives the smaller per-request timeout;
- local heuristic evidence-quote contract;
- empty, malformed, negative, zero, and positive worker extraction-limit parsing.

## Verification boundary

The current repair is merge/code eligible only after exact-head CI proves the regression suite, control policy, Observatory compatibility, tenant/RLS release gate, and production-container persistence. Review threads are resolved only against that exact-head evidence.

## Activation boundary

`BRAIN_REVENUE_EXTRACTION_ENABLED` remains explicit opt-in. This repair does not enable the feature, modify deploy configuration, call a live LLM provider, or perform any external revenue action.

Live provider cost/latency and labeled-real-feed extraction quality remain activation evidence to collect before enabling the flag in production; they are not replaced by unit/CI coverage.
