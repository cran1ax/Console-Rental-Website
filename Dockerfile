# ═══════════════════════════════════════════════════════════════════
# Corner Console — Production Dockerfile (multi-stage)
# ═══════════════════════════════════════════════════════════════════

# ──── Stage 1: Build dependencies ────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements/ requirements/
RUN pip install --no-cache-dir --prefix=/install -r requirements/prod.txt

# ──── Stage 2: Production image ──────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# Runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Create directories for logs, static, media
RUN mkdir -p /app/logs /app/staticfiles /app/media \
    && chown -R appuser:appuser /app

# Copy project files
COPY --chown=appuser:appuser . .

# Copy and set permissions for entrypoint
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Collect static files (uses a dummy SECRET_KEY for build time)
RUN DJANGO_SECRET_KEY=build-placeholder \
    DJANGO_ALLOWED_HOSTS=localhost \
    DATABASE_URL=sqlite:///tmp/db.sqlite3 \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "-c", "gunicorn.conf.py"]

