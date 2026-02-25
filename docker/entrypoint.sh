#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Corner Console — Docker Entrypoint
# ═══════════════════════════════════════════════════════════════════
#
# This script runs before the main CMD (gunicorn).
# It:
#   1. Waits for PostgreSQL to be ready
#   2. Runs database migrations
#   3. Collects static files
#   4. Execs into the CMD passed by Docker (gunicorn / celery / etc.)

set -e

echo "╔══════════════════════════════════════════════╗"
echo "║       Corner Console — Starting Up           ║"
echo "╚══════════════════════════════════════════════╝"

# ─── Wait for PostgreSQL ────────────────────────────────────────
if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Waiting for PostgreSQL..."

    # Extract host:port from DATABASE_URL
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:\/]*\).*/\1/p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_HOST=${DB_HOST:-db}
    DB_PORT=${DB_PORT:-5432}

    retries=30
    until python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('$DB_HOST', $DB_PORT))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null || [ $retries -eq 0 ]; do
        retries=$((retries - 1))
        echo "   Postgres not ready yet ($retries retries left)..."
        sleep 2
    done

    if [ $retries -eq 0 ]; then
        echo "❌ Could not connect to PostgreSQL at $DB_HOST:$DB_PORT"
        exit 1
    fi

    echo "✅ PostgreSQL is ready!"
fi

# ─── Run Migrations ────────────────────────────────────────────
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# ─── Collect Static Files ──────────────────────────────────────
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🚀 Starting: $@"
echo "═══════════════════════════════════════════════════"

# ─── Exec into the main process ────────────────────────────────
exec "$@"
