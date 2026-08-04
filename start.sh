#!/usr/bin/env bash
set -e

echo "==================================="
echo " Starting Flux Backend Server"
echo "==================================="

echo "[1/3] Running database migrations..."
python manage.py migrate --noinput

echo "[2/3] Seeding initial sysadmin account..."
python manage.py seed_admin || echo "Warning: seed_admin failed, continuing anyway..."

# Default port to 8000 if not provided by Railway
PORT="${PORT:-8000}"

echo "[3/3] Starting Gunicorn on port ${PORT}..."
exec gunicorn --bind 0.0.0.0:$PORT flux_core.wsgi:application
