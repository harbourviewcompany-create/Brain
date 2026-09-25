#!/usr/bin/env bash
# Cognitive Host Resurrection Protocol (CHRP) v1
# Original dual-path (Railway + Fly) recovery for Brain Runtime.
# Idempotent, zero-guesswork, self-documenting.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[CHRP]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

PROVIDER="${1:-both}"
SEED_PACK="${BRAIN_OBSERVATORY_SEED_PACK:-observatory-production-seed-v1}"
CORS_DEFAULT="https://brain-seven-puce.vercel.app,https://brain-harbourview.vercel.app,https://brain-git-main-harbourview.vercel.app"

require() { command -v "$1" >/dev/null 2>&1 || err "Missing required tool: $1"; }

check_env() {
  local missing=()
  [[ -z "${DATABASE_URL:-}" ]] && missing+=("DATABASE_URL")
  [[ -z "${BRAIN_API_KEY:-}" ]] && missing+=("BRAIN_API_KEY")
  if ((${#missing[@]})); then
    err "Required secrets not set: ${missing[*]}\nExport them or place in .env.production before running."
  fi
  ok "Core secrets present"
}

restore_railway() {
  log "=== Railway path ==="
  require railway
  if ! railway status >/dev/null 2>&1; then
    warn "No linked Railway project. Run: railway link"
    return 1
  fi

  log "Setting production variables..."
  railway variables set \
    BRAIN_ENV=production \
    BRAIN_CORS_ORIGINS="${BRAIN_CORS_ORIGINS:-$CORS_DEFAULT}" \
    BRAIN_VERCEL_OIDC_TEAM_SLUG=harbourview \
    BRAIN_VERCEL_OIDC_PROJECT=brain \
    BRAIN_VERCEL_OIDC_ENVIRONMENT=production \
    BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE=true \
    BRAIN_OBSERVATORY_SEED_PACK="$SEED_PACK" \
    BRAIN_INLINE_COGNITION=true \
    --skip-deploys || true

  railway variables set DATABASE_URL="$DATABASE_URL" BRAIN_API_KEY="$BRAIN_API_KEY" --skip-deploys || true

  log "Deploying with railway.brain-api-live.toml contract..."
  railway up --detach || railway redeploy --yes || true
  ok "Railway deploy triggered"
}

restore_fly() {
  log "=== Fly.io path ==="
  require fly
  local APP="${FLY_APP:-brain-api}"

  if ! fly status -a "$APP" >/dev/null 2>&1; then
    log "Creating Fly app $APP..."
    fly apps create "$APP" --org "${FLY_ORG:-personal}" 2>/dev/null || true
  fi

  log "Setting secrets..."
  fly secrets set -a "$APP" \
    DATABASE_URL="$DATABASE_URL" \
    BRAIN_API_KEY="$BRAIN_API_KEY" \
    BRAIN_CORS_ORIGINS="${BRAIN_CORS_ORIGINS:-$CORS_DEFAULT}" \
    BRAIN_VERCEL_OIDC_TEAM_SLUG=harbourview \
    BRAIN_VERCEL_OIDC_PROJECT=brain \
    BRAIN_VERCEL_OIDC_ENVIRONMENT=production \
    BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE=true \
    BRAIN_OBSERVATORY_SEED_PACK="$SEED_PACK" \
    BRAIN_INLINE_COGNITION=true

  log "Deploying (release_command applies migrations <=18 + seed)..."
  fly deploy -a "$APP" --config fly.toml

  log "Scaling app + worker..."
  fly scale count app=1 worker=1 -a "$APP" || true
  ok "Fly live. Check: fly status -a $APP"
}

print_vercel_handoff() {
  cat <<'HANDOFF'

═══════════════════════════════════════════════════════════
  Vercel hand-off (do this once the API is healthy)
═══════════════════════════════════════════════════════════

1. Vercel project "brain" → Settings → Environment Variables
2. Set / update:
   BRAIN_API_URL = https://<live-api-host>   (no trailing slash)
   BRAIN_API_KEY = <same value used above>
3. Redeploy production (or push any commit to main).

Verification:
  curl -s https://brain-seven-puce.vercel.app/api/brain-status | jq .
  # Expect: upstream_base filled, upstream_health_ok: true

Then open the Observatory — DEGRADED should clear and seeded beliefs appear.
HANDOFF
}

main() {
  log "Cognitive Host Resurrection Protocol (CHRP) v1"
  log "Provider target: $PROVIDER"
  check_env

  case "$PROVIDER" in
    railway) restore_railway ;;
    fly)     restore_fly ;;
    both)
      restore_railway || warn "Railway path incomplete — continuing with Fly"
      restore_fly || warn "Fly path incomplete"
      ;;
    *) err "Usage: $0 [railway|fly|both]" ;;
  esac

  print_vercel_handoff
  ok "CHRP finished. Dual-host resilience is now possible."
}

main "$@"
