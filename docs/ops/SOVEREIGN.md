# Sovereign Cognitive Kernel v3

Unique, fully cognitive, **self-hosted** on Vercel. No Railway. No Fly.

## v3 upgrades

| Mechanism | Behavior |
|-----------|----------|
| **Deterministic GWT** | Attention scores from FNV hash of tick + candidate — reproducible cycles |
| **Goal-conditioned attention** | Lexical overlap with active goals boosts workspace candidates |
| **Evidence binding** | Every revise attaches an endogenous evidence claim |
| **Coherence-based prediction resolve** | Hits/misses from belief confidence vs forecast, not coin-flips |
| **Identity digest** | Stable `identity_digest` recomputed from established beliefs |
| **Operator → goals** | Commands containing goal/priority language promote into the goal list |
| **Cron** | `*/5 * * * *` → `/api/cron/think` (4 cycles per run) |

## Enable

1. `BRAIN_API_URL` empty or Railway-rejected → automatic sovereign mode
2. Deploy from `main`
3. Optional: set `CRON_SECRET` and Vercel Cron Authorization header

## Surfaces

Beliefs, predictions, signals, evidence, contradictions, curiosity, organism, working-memory, learning-events, edges, tick, cron/think.

## Limits

Process-local store (warm instances keep state; cold starts re-seed bootstrap beliefs with stable IDs). Identity digest and deterministic scoring keep narrative continuity without a paid host.
