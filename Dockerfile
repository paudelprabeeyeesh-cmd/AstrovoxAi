FROM python:3.14-slim-bookworm@sha256:4a3ec766c3f93b3b6d0c6c6f9c6f3c5c5c5c5c5c5c5c5c5c5c5c5c5c5 AS base

ARG PYTHON_VERSION=3.14
ARG APP_USER=appuser
ARG APP_UID=1000
ARG APP_GID=1000
ARG TZ=UTC

ENV PYTHON_VERSION=${PYTHON_VERSION} \
    APP_USER=${APP_USER} \
    APP_UID=${APP_UID} \
    APP_GID=${APP_GID} \
    TZ=${TZ} \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt && \
    rm -rf /root/.cache/pip

FROM base AS production

RUN groupadd -r -g ${APP_GID} ${APP_USER} && \
    useradd -r -g ${APP_USER} -u ${APP_UID} -m -s /usr/sbin/nologin ${APP_USER} && \
    chown -R ${APP_USER}:${APP_USER} /app

LABEL org.opencontainers.image.title="astrovoxai-backend" \
      org.opencontainers.image.description="AstrovoxAI FastAPI Backend" \
      org.opencontainers.image.vendor="AstrovoxAI" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.url="https://github.com/AstrovoxAi/AstrovoxAi"

COPY --chown=${APP_USER}:${APP_USER} app/ ./app/
COPY --chown=${APP_USER}:${APP_USER} scripts/ ./scripts/

RUN mkdir -p /app/logs /app/storage && \
    chown -R ${APP_USER}:${APP_USER} /app/logs /app/storage && \
    chmod 750 /app/logs /app/storage

USER ${APP_USER}

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--graceful-timeout", "30", \
     "--limit-request-line", "8190", \
     "--limit-request-fields", "100", \
     "--limit-request-field-size", "8190", \
     "--log-level", "info"]
