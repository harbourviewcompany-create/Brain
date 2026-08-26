# Observatory module BUILD-READY traceability extension

BUILD-READY requires all owner object, schema, runtime service, state machine, fixtures, tests, acceptance criteria, audit events and GO/HOLD status evidence to be complete. Production remains HOLD until Vercel is rewired and parity is proven.

| Module | owner object | schema | runtime service | state machine | fixtures | tests | acceptance criteria | audit events | GO/HOLD status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `apps/observatory/src/app/page.tsx`; `apps/observatory/src/components/observatory/BrainObservatory.tsx`; `apps/observatory/src/hooks/useBrainObservatory.ts`; `apps/observatory/src/lib/observatory.ts` | Brain Observatory frontend | typed Observatory models | Next.js Observatory | BFF reads -> deterministic UI state | structural verifier | frontend verify + visual evidence | source parity and responsive root render | OBSERVATORY_STRUCTURAL_VERIFICATION | HOLD |
| `apps/observatory/src/app/api/brain/[...path]/route.ts`; `apps/observatory/src/lib/brain-upstream.ts` | browser-safe BFF | allowlisted proxy contract | Next.js route handler | request -> OIDC/key -> Railway -> no-store response | structural verifier | frontend verify + production read audit | fail-closed auth and no secret exposure | OBSERVATORY_BFF_IDENTITY_VERIFIED | HOLD |
