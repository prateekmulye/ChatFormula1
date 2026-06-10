# Multi-stage build for the ChatFormula1 agent service with Poetry
# Stage 1: Builder - install dependencies
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=2.2.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry --version

COPY pyproject.toml poetry.lock* ./

# Install dependencies only (the application is copied in the next stage)
RUN poetry install --no-root --only main --no-interaction --no-ansi

# Stage 2: Production - minimal runtime image
FROM python:3.12-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src:/app \
    ENVIRONMENT=production

WORKDIR /app

# curl is needed for the container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser ingestion/ ./ingestion/

USER appuser

EXPOSE 8000

# All routes (including health) require the internal bearer token
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f -H "Authorization: Bearer ${INTERNAL_API_TOKEN}" \
        http://localhost:8000/internal/health || exit 1

CMD ["uvicorn", "chatf1_agent.server:app", "--host", "0.0.0.0", "--port", "8000"]
