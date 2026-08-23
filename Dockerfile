# Brain Runtime API — production image
# Target: Railway, Fly.io, or any Docker host
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BRAIN_ENV=production \
    BRAIN_EXTERNAL_ACTIONS_ENABLED=false

WORKDIR /app

# System deps for psycopg binary wheels / health
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Dependency layer (cached across builds) ---
# Install dependencies from pyproject.toml before copying source, so this layer
# only invalidates when pyproject.toml or constraints.txt changes -- not on
# every code change. constraints.txt pins exact transitive versions so two
# builds on two different days resolve the same dependency graph.
COPY pyproject.toml README.md constraints.txt ./
RUN mkdir -p brain apps db \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -c constraints.txt .

# --- Source layer ---
COPY brain ./brain
COPY apps ./apps
COPY db ./db

# Re-install the local package itself (fast -- deps already satisfied above).
RUN pip install --no-cache-dir --no-deps .

# Railway/Fly inject PORT; default 8000 for local docker run
ENV PORT=8000
EXPOSE 8000

# Run as a non-root user
RUN groupadd --system brain && useradd --system --gid brain --home-dir /app brain \
    && chown -R brain:brain /app
USER brain

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT}"]
