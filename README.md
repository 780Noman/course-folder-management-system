# Course Folder Management System

A cloud-based system for UIIT (PMAS Arid Agriculture University Rawalpindi) where
faculty upload, per course, the documents required by the official Course
Assessment checklist; an admin (focal person) reviews each folder, flags missing
items, and issues a Course Folder Review Certificate once everything required is
complete.

## Highlights

- Two roles — Admin (focal person) and Faculty — with server-side access control.
- Per-course folders with a flexible, two-phase (mid / final) checklist.
- Worst / Average / Best sample grouping and "Not Applicable" items.
- Secure cloud file storage with on-demand signed-URL viewing and image thumbnails.
- Admin review with red-flagged missing items, certificate PDF generation, and
  certified/pending reports.
- Full multi-term history (Spring / Fall / Summer, year by year).

## Stack

Python 3.12 · Django 5.2 LTS · PostgreSQL · Tailwind + HTMX · cloud object
storage (Cloudflare R2 / S3) · WeasyPrint · Docker.

## Getting started

See `MANUAL_SETUP.md` for first-time setup, then `PLAN.md` for the build phases.
`CLAUDE.md` holds the working rules and `docs/DATA_MODEL.md` the schema.
`docs/BACKUPS.md` documents database + object-storage backup and restore.

### Security

- Roles enforced server-side on every view; folder writes are owner-only,
  reads are owner-or-admin (focal-person review).
- Uploads are private; files are served only via short-lived signed URLs
  (or a guarded streamed response locally).
- Production sets HTTPS redirect, HSTS, secure/HttpOnly cookies, CSRF, security
  headers, and login rate-limiting/lockout. Verify with:

  ```bash
  python manage.py check --deploy
  pip install pip-audit && python -m pip_audit   # dependency vulnerability scan
  ```

```bash
cp .env.example .env      # fill in values
docker compose up         # app at http://localhost:8000
```

### Local (without Docker)

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate                       # uses local SQLite when DATABASE_URL is unset
python manage.py runserver
```

Settings live in `config/settings/{base,dev,prod}.py` and are loaded entirely
from the environment via `django-environ`. `manage.py` defaults to
`config.settings.dev`; `wsgi`/`asgi` default to `config.settings.prod`.

### First admin (one-time)

The system has no public sign-up. Create the first focal-person (admin) account
once with Django's `createsuperuser`; it prompts for email, name, and password
and is assigned the **ADMIN** role automatically. That admin then invites all
other users from the dashboard.

```bash
python manage.py createsuperuser          # local
docker compose run --rm web python manage.py createsuperuser   # Docker
```

Everyone else is onboarded via the invite flow (admin enters a name + email; the
user receives a single-use, expiring link and sets their own password).

### Demo admin (evaluation only)

For a throwaway focal-person login to try the system, run the idempotent
`create_demo_admin` command. It creates-or-refreshes a single account
(`tester@gmail.com` / `tester@123`) and never touches any other user — the real
admin included. Re-run it any time to reset the demo password.

> **Security note:** this is a well-known credential with full focal-person
> access (but no Django `/admin/` access). Use it only for evaluation and
> **remove the account afterwards**; do not leave it on a real deployment.

```bash
python manage.py create_demo_admin          # local
docker compose -f docker-compose.prod.yml exec web python manage.py create_demo_admin   # server
```

### Building CSS (Tailwind)

CSS is compiled with the Tailwind **standalone CLI** (no Node required). Download
the binary once into `bin/` (git-ignored), then build:

```bash
# one-time: download bin/tailwindcss(.exe) for your OS from the Tailwind v3 release
./bin/tailwindcss -i assets/css/input.css -o static/css/app.css --minify
# during development, add --watch to rebuild on change
```

`assets/css/input.css` is the source; `static/css/app.css` (committed) is what the
templates load and WhiteNoise serves.
