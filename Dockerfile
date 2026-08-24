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

CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT}"]
