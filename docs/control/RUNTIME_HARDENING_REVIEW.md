# Runtime hardening review — source record

Label: **SOURCE**

Findings from a repository review at `30d45d4`, and what was changed to close them.
Every gate the repository defines was green at that commit — 570 tests, ruff, both
validators, and the Observatory build — so these are defects no existing check looked
for. Each was reproduced by execution before being fixed, and each fix is held by a
regression test named below.

## Findings and resolutions

### 1. The Observatory BFF was an unauthenticated public relay

`apps/observatory/src/app/api/brain/[...path]/route.ts` accepted GET, POST, PUT, PATCH
and DELETE from any caller, checked only that the first path segment was allowlisted,
then attached the server-side `BRAIN_API_KEY` and forwarded. No `middleware.ts` existed.
The allowlist admitted `learn`, `signals`, `outcomes`, `approvals`, `tick`,
`revenue-signals`, `daily-revenue-report` and the whole `organism` tree, so anyone who
knew the deployment URL could write beliefs, drive cognition ticks and approve agency
actions. The API key protected the Railway hostname, not the Brain.

**Resolved.** `apps/observatory/src/middleware.ts` requires a signed operator session on
every route except `/login` and the auth endpoints. `src/lib/operator-session.ts` issues
and verifies HttpOnly, SameSite=Lax, 12-hour sessions over Web Crypto HMAC-SHA256, with
the expiry covered by the signature. Absent `OBSERVATORY_ACCESS_KEY` or
`OBSERVATORY_SESSION_SECRET`, the middleware refuses every request rather than falling
open. Held by `apps/observatory/scripts/test-operator-session.mjs` and by structural
assertions in `scripts/verify-observatory.mjs`, both in `npm run verify`.

### 2. A bearer token masked a valid API key

`apps/api/main.py` read the API key from `X-Brain-Api-Key`, then unconditionally
overwrote its candidate with anything in an `Authorization: Bearer` header and compared
that against `BRAIN_API_KEY`. The BFF sends both, so a correct key returned 401.
Reproduced: both headers → 401; key alone → 200.

Note on scope: server-side OIDC verification does exist, in `tools/vercel_oidc.py`,
applied by `VercelOidcAuthBridge` in `tools/live_cockpit_routes.py`. That bridge wraps
only the `Dockerfile.railway` entrypoint. The canonical `Dockerfile` entrypoint
(`apps.api.tenant_app`) has no bridge and authenticates on `BRAIN_API_KEY` alone, which
is where the collision bit.

**Resolved.** `brain/security.py` gained `credential_candidates` and
`presented_credentials`: every recognized credential header is collected and the caller
is authorized if any one matches, each comparison constant-time. `ApiKeyAuthenticator`
shares the same path. `apps/observatory/README.md` now names which image verifies OIDC
instead of implying both do. Held by `tests/test_credential_precedence.py`.

### 3. Evidence was never deduplicated

`BeliefEngine.apply_evidence` applied a fixed additive nudge per submission with no check
for whether that source had already made that claim. Posting an identical claim and
source to `/learn` three times walked a belief from 0.5 to certainty. Re-applying one
`Evidence` object reached confidence 1.0 while `supporting_evidence` held a single item.

**Resolved.** `evidence_fingerprint` identifies an assertion by source, normalized claim
and stance. A repeat attaches to provenance and moves confidence by zero. Distinct
corroboration still accumulates, now with harmonic damping per side, so confidence tracks
the breadth of evidence rather than the volume of submissions. Fingerprints are derived
state: `PostgresBrainStore.hydrate` rebuilds them from the evidence rows it already
holds, and `belief.updated` carries them so an event-replayed cache restores them too.
Held by `tests/test_belief_evidence_integrity.py`.

### 4. CONTESTED was an absorbing state

Evidence sets only grow and the contested branch preceded every confidence threshold, so
one contradicting item pinned a belief to `contested` permanently. Verified: one
contradiction plus twenty maximally reliable corroborations gave confidence 1.0, state
`contested`. Such a belief could never reach `rejected` either.

**Resolved.** State is recomputed from the current evidence balance. A belief is contested
only while the minority side holds at least `1/contested_ratio` of the majority's distinct
assertions; otherwise the confidence thresholds decide, and a previously contested belief
falls back to `hypothesis` rather than re-latching. Held by the same test file.

### 5. The cognition worker never opened the database it validated

`build_runner()` called `build_default_heartbeat()` with no event store, so the continuous
loop ran on `InMemoryBrainStore` regardless of `DATABASE_URL`. `worker_database_url()` —
and the tenant-RLS role topology it enforces — ran only under `BRAIN_WORKER_MODE=verify`.
Everything the worker produced was invisible to the API and discarded on restart.

**Resolved.** `build_brain_store()` validates the role topology and returns a
`PostgresBrainStore` when a DSN is configured; `build_runner()` uses it, and the learning
service now shares the runner's store instead of opening a second one. With no DSN the
worker still runs, but says so at WARNING rather than degrading silently. Held by
`tests/test_worker_persistence.py`.

### 6. Per-tenant service bundles were unbounded and raced

`TenantPartitionedFactory.instances` grew one entry per tenant for the process lifetime,
each holding a full in-memory projection of that tenant's belief graph. The check-then-set
was unsynchronized, and FastAPI runs sync handlers in a threadpool, so two concurrent
first-requests for one tenant could each build an instance and silently discard one —
losing every mutation written to the orphan.

**Resolved.** An LRU map under an `RLock`, capped by `BRAIN_TENANT_BUNDLE_LIMIT`
(default 64). The system partition is never evicted; evicted bundles are closed. Eviction
drops only the in-memory projection, since PostgreSQL remains authoritative. Held by
`tests/test_tenant_partition_bounds.py`, including a concurrency test.

### 7. Nothing was logged, and 26 handlers swallowed exceptions

`import logging` appeared in one file repo-wide and nowhere in `brain/` or `apps/`. Of 50
broad `except Exception` handlers, 26 discarded the error — twelve of them in the
continuous cognition loop.

**Resolved.** `brain/logging_config.py` provides idempotent JSON logging on the `brain`
logger tree, leaving the root logger alone. Every silent handler in `brain/runner.py`,
`brain/mind_runtime.py` and `apps/worker/main.py` now reports what failed with a specific
message. Workflow code uses `workflow.logger` to stay replay-safe. The one remaining
`pass` is a named, benign `WorkflowAlreadyStartedError`.

### 8. The two Railway images served different route sets

Nine collection routes the Observatory client calls existed only in
`tools/live_cockpit_routes.py`, served by `Dockerfile.railway` — the image its own header
calls the legacy compatibility image. `railway.toml` and both Docker CI jobs build
`Dockerfile`, which served none of them, so CI proved out an image the cockpit would 404
against.

**Resolved.** The read model moved to `apps/api/cockpit_read_routes.py` and is registered
on the canonical app. `tests/test_canonical_image_route_surface.py` asserts every route
the client calls is served and authenticated, and fails if a client function is added
against a route the API never gained.

### 9. Live cockpit views rendered fabricated data

`beliefs` and `predictions` seeded React state with `MOCK_` arrays, so before the first
fetch resolved — and permanently if it failed — operators saw invented records rendered
identically to real ones. `approvals` was mock-only behind Approve and Reject buttons
that did nothing. `health` fell back to a fixture, rendering a green `ok` while the
runtime was unreachable.

**Resolved.** `useBrainResource` and the `ResourceState` components give every live view
explicit loading, error and empty states with no fallback data. `approvals` is wired to
`/organism/agency-actions` and `/organism/agency/approve`, so the buttons do what they
say. `scripts/verify-observatory.mjs` fails the build if these routes reintroduce mock
imports.

### 10–12. Deployment hygiene

`BRAIN_TENANT_MODE` and `BRAIN_TENANT_CONTEXT_SECRET` were undocumented despite being
mandatory for tenant mode; `next build` rewrote a tracked `next-env.d.ts` and left an
ungitignored `tsconfig.tsbuildinfo`, so a build broke lint on its own second run; and two
migrations shared version `006`, which `--max-version` and the CI baseline gate cannot
distinguish.

**Resolved.** `.env.example` documents the tenant and Observatory variables;
`next-env.d.ts` and `*.tsbuildinfo` are gitignored and eslint-ignored; and
`_assert_unique_versions` refuses a new duplicate migration version while grandfathering
the two `006` files, which are long applied and cannot be renamed without orphaning their
`brain_schema_migrations` rows. `scripts/validate_control_layer.py` also no longer scans
`node_modules`, which made it fail after a frontend install.

## Verification

`pytest`, `ruff check .`, `tools/validate_agent_control.py`,
`tools/validate_mod_008_015_conformance.py`, `scripts/validate_control_layer.py` and
`npm --prefix apps/observatory run verify`.
