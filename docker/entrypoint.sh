#!/bin/sh
# Production container entrypoint: apply migrations and gather static files,
# then exec the container command (Gunicorn by default).
#
# Note: for multi-instance deployments, move `migrate` to a one-off release/
# pre-deploy step so concurrent instances don't race on schema changes.
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Ensuring cache table exists (login lockout counters)..."
python manage.py createcachetable

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"
