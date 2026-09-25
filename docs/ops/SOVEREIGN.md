# Sovereign Cognitive Kernel v2

Unique, fully cognitive, **self-hosted** on Vercel. No Railway. No Fly.

## Architecture (original)

Not an LLM wrapper. A small event-sourced mind with explicit mechanisms:

| Mechanism | Behavior |
|-----------|----------|
| **Global Workspace competition** | Curiosity, contested beliefs, open predictions, and endogenous self-queries compete; winner enters working memory |
| **Belief lattice** | States: hypothesis → provisional → established / contested / rejected; confidence revised by prediction hits/misses |
| **Circadian phases** | `wake → attend → revise → predict → dream → rest` — each phase does different work |
| **Prediction loop** | Open forecasts resolve stochastically; misses lower confidence and open curiosity |
| **Dream associations** | Sparse edges + occasional contradiction detection under confidence divergence |
| **Self-model** | observing / integrating / uncertain / revised |
| **Operator intake** | `POST /api/brain/signals` injects high-priority attention |

## Enable

1. Clear **`BRAIN_API_URL`** on Vercel project `brain`
2. Merge PR + redeploy
3. Optional Cron: `GET /api/cron/think` every few minutes

## Surfaces

- `/api/brain/beliefs`, `/predictions`, `/signals`, `/contradictions`, `/curiosity`, `/organism`, `/working-memory`, `/learning-events`, `/edges`
- `/api/brain/tick` (POST), `/api/cron/think`
- `/api/brain-status` → `mode: "sovereign"`, advances one cycle per poll

## Limits

Process-local memory (warm instance keeps state; cold start re-seeds). Upgrade path remains optional Turso Path B without reintroducing Railway/Fly.
