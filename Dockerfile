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

COPY pyproject.toml README.md ./
COPY brain ./brain
COPY apps ./apps
COPY db ./db

RUN pip install --upgrade pip && pip install .

# Railway/Fly inject PORT; default 8000 for local docker run
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT}"]
