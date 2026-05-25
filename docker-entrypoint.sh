#!/bin/sh
set -e

echo "Running database migrations..."
flask --app wsgi db upgrade

echo "Seeding default data..."
flask --app wsgi seed-defaults

echo "Starting Gunicorn..."
exec gunicorn \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --access-logfile - \
  --error-logfile - \
  wsgi:app
