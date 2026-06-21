# Deployment Runbook

Production runs the Docker image (`Dockerfile`) with **Gunicorn** behind an
HTTPS-terminating proxy, a **managed PostgreSQL** database, **Cloudflare R2**
(or S3) for files, and an **SMTP** email provider.

The image entrypoint (`docker/entrypoint.sh`) runs `migrate` and `collectstatic`
on start, then launches Gunicorn (`config/gunicorn.py`). Static files are served
by WhiteNoise (compressed + hashed); uploaded files are private in R2 and served
via short-lived signed URLs.

> This codebase ships everything in Task 1 (image, Gunicorn, collectstatic,
> entrypoint, compose). Tasks 2–4 below require your accounts/credentials and DNS;
> follow them in order.

---

## 0. Pre-flight (once)

- Generate a real secret key:
  `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- Decide the host: **Render/Railway** (managed, simplest) or **Hetzner + Coolify**
  (self-host, uses `docker-compose.prod.yml`).
- Have a domain ready (e.g. `folders.uiit.edu.pk`).

---

## 1. Image / app config

Environment variables the app needs in production (see `.env.example`):

| Variable | Value |
|----------|-------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `SECRET_KEY` | long random string (never commit) |
| `DEBUG` | `False` (prod default) |
| `ALLOWED_HOSTS` | your domain(s), comma-separated |
| `DATABASE_URL` | from the managed database |
| `AWS_*` | R2/S3 bucket + credentials (section 3) |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | SMTP provider (section 3) |
| `WEB_CONCURRENCY` | worker count (e.g. 3) |

`wsgi.py`/`asgi.py` already default to `config.settings.prod`.

---

## 2. Deploy + managed PostgreSQL

### Option A — Render / Railway (managed)

1. Create a **PostgreSQL** instance; copy its connection string to `DATABASE_URL`.
2. Create a **Web Service** from this repo; it auto-detects the `Dockerfile`.
   - No start command needed (the image's entrypoint + CMD handle migrate,
     collectstatic, and Gunicorn).
3. Set all environment variables from section 1 in the service dashboard.
4. Deploy. Watch logs for "Running database migrations" → "Collecting static
   files" → Gunicorn boot.

### Option B — Hetzner + Coolify (self-host)

1. Provision a server; install Docker + Coolify (or use Compose directly).
2. Put production values in `.env` (including `POSTGRES_PASSWORD`).
3. `docker compose -f docker-compose.prod.yml up -d --build`
   - Brings up Postgres (with healthcheck) and the web service.
4. Front it with a TLS proxy (Caddy/Traefik/Nginx) — see section 4.

**Multi-instance note:** the entrypoint runs `migrate` on each start. If you run
more than one web instance, move `migrate` to a one-off release/pre-deploy
command and keep only `collectstatic` + Gunicorn in the entrypoint.

---

## 3. Object storage (R2) + email

### Cloudflare R2 (or S3)

1. Create a **private** bucket (e.g. `coursefolders-prod`). Do **not** enable
   public access.
2. Create an API token / access key scoped to that bucket.
3. Set:
   - `AWS_STORAGE_BUCKET_NAME` = bucket name
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - `AWS_S3_ENDPOINT_URL` = your R2 S3 endpoint
     (`https://<accountid>.r2.cloudflarestorage.com`)
   - `AWS_S3_REGION_NAME` = `auto`
4. When `AWS_STORAGE_BUCKET_NAME` is set, the app switches to private S3 storage
   with signed URLs automatically (`config/settings/base.py`).
5. Enable **versioning** + a backup mirror (see `docs/BACKUPS.md`).

### Email (SMTP)

University SMTP or Brevo free tier:
`EMAIL_HOST`, `EMAIL_PORT` (587), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS=True`, `DEFAULT_FROM_EMAIL`. Send a test invite to confirm delivery
(invites and password resets depend on this).

---

## 4. HTTPS, domain, first admin, smoke test

1. **DNS**: point your domain at the host; set `ALLOWED_HOSTS` accordingly.
2. **HTTPS**: terminate TLS at the platform (Render/Railway automatic) or the
   reverse proxy (Caddy/Traefik auto-cert). The app sets HSTS and redirects HTTP
   → HTTPS (`SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`); ensure the proxy
   sends `X-Forwarded-Proto: https`.
3. **First admin** (one-time):
   ```bash
   # Render/Railway: run in a one-off shell
   python manage.py createsuperuser
   # Compose:
   docker compose -f docker-compose.prod.yml run --rm web python manage.py createsuperuser
   ```
   This creates the focal-person (ADMIN) account; it then invites all faculty.
4. **Smoke test every role flow** on the live site:
   - [ ] Admin logs in → admin dashboard.
   - [ ] Admin creates a term (mark current), a course assigned to a faculty.
   - [ ] Admin invites a faculty member → invite email arrives → faculty sets
         password via the one-time link → faculty dashboard.
   - [ ] Faculty opens the course folder, uploads a file (validates; thumbnail
         for images), marks an item N/A, adds a quiz; submits mid-term.
   - [ ] Admin reviews, flags an item + returns; faculty sees the flag, fixes,
         resubmits; admin approves mid, then final.
   - [ ] Admin issues the certificate → PDF downloads (faculty can download too).
   - [ ] Admin report + PDF/Excel export; admin "Find courses" live search.
   - [ ] Confirm a file URL works only while signed-in (signed URL expires).

---

## 5. Post-deploy verification

```bash
python manage.py check --deploy     # 0 issues expected
python -m pip_audit                  # no known vulnerabilities
```

- Confirm backups are scheduled and a test restore works (`docs/BACKUPS.md`).
- Production uses Django's local-memory cache for login lockout by default; for
  multiple web workers, configure a shared cache (Redis/Memcached) so the
  lockout holds across processes.
