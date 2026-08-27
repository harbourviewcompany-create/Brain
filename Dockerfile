FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BRAIN_ENV=production \
    BRAIN_EXTERNAL_ACTIONS_ENABLED=false

WORKDIR /app

# Dependency layer: invalidate only when dependency metadata changes.
COPY pyproject.toml README.md constraints.txt ./
RUN mkdir -p brain \
    && python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -c constraints.txt .

# Source layer: keep normal code changes out of the dependency cache key.
COPY brain ./brain
COPY apps ./apps
COPY db ./db
# tools/ carries the Railway deployment identity bridge and the migration
# runner named by railway.toml's preDeployCommand. Omitting it produced an
# image that could neither verify a Vercel OIDC bearer nor apply migrations.
COPY tools ./tools
RUN python -m pip install --no-cache-dir --no-deps --force-reinstall . \
    && python -m pip check

# Run the production API without root privileges.
RUN groupadd --system brain \
    && useradd --system --gid brain --home-dir /app brain \
    && chown -R brain:brain /app
USER brain

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/ready', timeout=4).read()" || exit 1

# live_cockpit_routes is apps.api.tenant_app plus the Vercel OIDC bridge, and
# nothing else: it imports that app object rather than building a second one.
# tenant_app itself preserves legacy single-tenant behavior when
# BRAIN_TENANT_MODE=disabled and installs signed membership/RLS enforcement
# when tenant mode is enabled. Serving the bridged app here keeps every Railway
# path -- railway.toml, railway.brain-api-live.toml, Dockerfile.railway -- on
# one runtime surface.
CMD ["sh", "-c", "python -m uvicorn tools.live_cockpit_routes:app --host 0.0.0.0 --port ${PORT}"]
