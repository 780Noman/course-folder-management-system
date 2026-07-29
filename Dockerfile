FROM python:3.12-slim

# Runtime system libs for WeasyPrint (cairo, pango, gdk-pixbuf) + fonts so the
# certificate/report PDFs render text correctly. psycopg[binary] and Pillow ship
# as wheels, so no build toolchain is needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8 \
    fonts-dejavu-core fonts-liberation gosu \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create the non-root user and the volume mount points, owned by that user.
# The container starts as root ONLY so the entrypoint can fix the ownership of
# the media/ volume (a fresh Docker named volume is root-owned); it then drops
# to this unprivileged user with gosu before running anything.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R app /app

EXPOSE 8000

# Fix volume ownership, migrate + collectstatic, then start Gunicorn as `app`.
# Invoked via `sh` so it does not depend on the executable bit surviving a
# non-POSIX build context.
ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "-c", "config/gunicorn.py"]
