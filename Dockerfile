FROM python:3.12-slim

# Runtime system libs for WeasyPrint (cairo, pango, gdk-pixbuf) + fonts so the
# certificate/report PDFs render text correctly. psycopg[binary] and Pillow ship
# as wheels, so no build toolchain is needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8 \
    fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user.
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000

# migrate + collectstatic, then start Gunicorn. Invoked via `sh` so it does not
# depend on the executable bit surviving a non-POSIX build context.
ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "-c", "config/gunicorn.py"]
