# Brain Zero-Dollar Runtime

## Authority

This control applies to the Brain production-runtime migration from Railway/PostgreSQL to Vercel + Turso/libSQL + GitHub Actions. The governing machine-readable policy is `docs/control/zero_cost_policy.json`.

The hard financial invariant is **USD 0 paid compute/storage budget with paid overage disabled**. A free tier becoming unavailable is a blocker, not permission to create a paid replacement.

## Target runtime

- **Vercel Hobby** serves the stateless FastAPI runtime and Observatory.
- **Turso/libSQL free tier** is canonical durable persistence for the zero-dollar production runtime.
- **GitHub-hosted standard Actions** runs bounded scheduled maintenance and the manual migration/rescue workflow.
- **Railway** is not a production dependency after cutover. Until retirement is separately approved, it remains a read-only migration source and rollback evidence surface only.

No component may create a paid resource or opt into paid overage.

## Persistence contract

`brain/adapters/persistence.py` defines provider-neutral event and projection contracts. Turso must preserve the observable semantics of the existing PostgreSQL stores:

1. append-only event identity and idempotency by event UUID;
2. `causation_id` and `correlation_id` preservation;
3. deterministic chronological replay ordered by `(occurred_at, id)`;
4. bounded newest-first `read_recent` by event type;
5. strict cursor semantics for `read_after`;
6. projection-checkpoint save/get equivalence;
7. replay across hot events and immutable compressed archive segments;
8. duplicate-event rejection/idempotency even after a hot event has been compacted into an archive segment.

Canonical cognitive events and disposable telemetry are separate data classes. Storage pressure may prune disposable telemetry according to policy. It must never silently discard a canonical event.

## Storage pressure

The logical storage budget is 5 GiB. Threshold behavior is defined in `brain/storage_policy.py` and mirrored by the machine-readable policy:

- 60%: observe/report pressure;
- 70%: compact eligible historical canonical events into immutable gzip NDJSON segments;
- 80%: prune disposable telemetry according to retention rules;
- 85%: reject noncanonical growth and surface a degraded/blocked state rather than allowing uncontrolled expansion.

Every immutable archive segment carries a SHA-256 digest and must verify before hot rows are deleted. Replay must verify a segment before accepting its contents.

## Stateless cognition

The Vercel entrypoint is `api/index.py`. It binds Turso persistence, disables the long-lived inline cognition daemon, and fails closed if the PostgreSQL tenant-RLS runtime is requested.

Cognition occurs through bounded request-triggered cycles and idempotent scheduled maintenance. Existing API/BFF contracts remain unchanged. PostgreSQL tenant/RLS release tests remain as a security regression suite; the zero-dollar Turso path does not claim or emulate PostgreSQL RLS semantics.

## Vercel release control

Repository-controlled deployment rules live in `vercel.json` and `scripts/vercel-ignore-build.sh`.

- automatic non-main Git deployments are disabled;
- the ignored-build command returns `0` for non-main or irrelevant main commits;
- it returns `1` only when a main commit changes runtime/Observatory-relevant files;
- the first main deployment without a known previous deployment SHA builds conservatively.

PR validation is therefore completed before a change can reach the protected main release path.

## Railway rescue invariant

The rescue workflow is manual (`workflow_dispatch`) only. It uses the repository secret `RAILWAY_TOKEN` and MUST NOT mutate, delete, restart, redeploy, migrate, vacuum, rewrite, or otherwise alter the Railway source volume/database.

The workflow sequence is:

1. authenticate to Railway using the secret without printing it;
2. download/copy the existing PostgreSQL volume or data export into an ephemeral GitHub runner workspace in read-only/source-preserving mode;
3. make a second runner-local working copy;
4. perform any PostgreSQL recovery/startup only against that runner-local working copy;
5. enumerate every non-system persistent table and schema object needed for complete data recovery;
6. export deterministic source datasets and counts;
7. convert the complete persistent dataset into a Turso-compatible SQLite database;
8. generate deterministic source and destination row-count manifests and SHA-256 integrity manifests;
9. independently verify the SQLite result before any remote import is enabled;
10. import only into an already-existing free Turso database provided through `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`;
11. verify destination counts and event/replay equivalence after import;
12. upload migration evidence artifacts.

The workflow contains no command that creates a Turso database, upgrades a plan, enables overage, deletes Railway data, or mutates the Railway source.

## Maintenance

Scheduled GitHub Actions maintenance is bounded and protected with workflow concurrency. Each invocation performs a finite cognition tick budget, telemetry pruning, archive compaction, checkpoint work, and storage reporting. Re-running the same maintenance window must be idempotent at the durable event/storage boundary.

## Cutover gates

### Code merge GO

Requires all of the following:

- full Python test suite green;
- Turso contract/equivalence suite green;
- migration tooling fixture verification green;
- Ruff/type/static checks green;
- Observatory verification/build green;
- zero-cost policy validator green;
- Vercel build filter tests green;
- browser desktop/tablet/mobile evidence generated by CI where supported;
- no unresolved regression in PostgreSQL tenant/RLS security tests.

### Production cutover GO

In addition to code-merge GO:

- Railway rescue successfully completed from the real source without source mutation;
- every persistent source table enumerated;
- deterministic source/destination counts match or documented transformations reconcile exactly;
- SHA-256 migration manifests verify;
- canonical Brain event counts and event/replay equivalence verify;
- Turso storage usage is below the zero-cost pressure ceiling;
- Vercel production health reports `persistence=turso` and healthy storage pressure;
- live API/BFF and Observatory desktop/tablet/mobile audit passes;
- production deployment SHA/ID is recorded.

### Railway retirement GO

Requires production cutover GO plus an explicit separate retirement decision after a stable observation window and retained migration evidence. This migration does not delete or modify the Railway source.

## Evidence

Migration artifacts must include at minimum:

- source table inventory;
- source row-count manifest;
- destination row-count manifest;
- source export SHA-256 manifest;
- SQLite database SHA-256;
- archive-segment hashes where present;
- event/replay equivalence report;
- storage-usage report;
- workflow/run IDs;
- Vercel deployment ID/SHA;
- production health payload;
- desktop/tablet/mobile screenshots.

Missing real production evidence is a HOLD, not an inferred pass.
