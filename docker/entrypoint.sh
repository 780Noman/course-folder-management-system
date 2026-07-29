#!/bin/sh
# Production container entrypoint.
#
# Runs as root ONLY to fix the ownership of the media/ (uploads + certificates)
# and staticfiles/ directories: a fresh Docker named volume is owned by root,
# which the unprivileged `app` user cannot write to -- that is what makes an
# upload fail with "could not be saved". After fixing ownership it applies
# migrations and static files and drops to `app` (via gosu) for every process.
#
# Note: for multi-instance deployments, move `migrate` to a one-off release/
# pre-deploy step so concurrent instances don't race on schema changes.
set -e

# Make the uploads/certificates + static volumes writable by the app user
# (idempotent and cheap once ownership is correct).
chown -R app /app/media /app/staticfiles 2>/dev/null || true

echo "Running database migrations..."
gosu app python manage.py migrate --noinput

echo "Ensuring cache table exists (login lockout counters)..."
gosu app python manage.py createcachetable

echo "Collecting static files..."
gosu app python manage.py collectstatic --noinput

exec gosu app "$@"
