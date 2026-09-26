# Sovereign Cognitive Kernel v4

Unique, fully cognitive, self-hosted on Vercel. No Railway. No Fly.

## v4 upgrades

- **First lap on seed** — six endogenous cycles so first paint has hypothesis, prediction, evidence, focus.
- **Goal lock** — operator commands dominate attention for 8 cycles.
- **Focus-bound evidence** — attend/revise attach claims that retrieval can score.
- **GET /api/brain/explain** — last cycle winner, score, phase, delta.
- **GET /api/brain/snapshot** — compact in-process state (process-local until DATABASE_URL is wired on this deployment).

## Enable

`BRAIN_API_URL` empty or Railway-rejected → sovereign mode.

## Limits

Process-local store. Cold start re-seeds then immediately runs the first lap.
