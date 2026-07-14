# CLAUDE.md

Project guidance for AI coding assistants working in this repository. Read this
file fully before generating or changing any code.

## 1. What this project is

A **Course Folder Management System** for UIIT (University Institute of
Information Technology), PMAS Arid Agriculture University Rawalpindi.

Faculty members upload, per course they teach, the documents required by the
official **Course Assessment / Course Folder Review** checklist. A focal-person
(admin) reviews each folder, missing items are flagged, and a **Course Folder
Review Certificate** is generated once all required items are complete.

The system runs on the public cloud and must be secure, reliable, and easy to
use for non-technical faculty.

## 2. Roles

- **Admin (Focal Person):** full access. Creates/removes faculty, reviews every
  course folder, flags missing items, issues certificates, generates reports,
  views any faculty member's data.
- **Faculty:** sees only their own courses and folders. Uploads, edits, deletes
  their own items and submits folders for review.

A single login page routes each user to the correct dashboard based on role.
Role checks are enforced **server-side**, never only in the UI.

## 3. Tech stack (do not change without updating PLAN.md)

- Python 3.12, **Django 5.2 LTS**
- PostgreSQL (psycopg 3)
- Templates + **Tailwind CSS** + **HTMX** + light **Alpine.js** (no SPA, no DRF
  for v1; HTMX returns HTML partials for interactivity such as async uploads,
  live filtering, and review actions)
- Gunicorn + WhiteNoise
- Cloud object storage via `django-storages` + `boto3` (Cloudflare R2 /
  S3-compatible) for all uploaded files
- Pillow for image thumbnails
- WeasyPrint for certificate PDF generation (HTML template -> PDF)
- pytest + pytest-django for tests
- Docker + docker-compose for dev/prod parity

## 4. Working discipline (strict)

These rules are non-negotiable:

1. **Verify before acting.** Never guess. Confirm a function, field, or behavior
   exists before relying on it. If something is unknown, inspect the code or ask.
2. **Plan before code.** Follow `PLAN.md`. Work one task at a time, in order.
3. **No blind patching.** Do not "fix" by trial and error. Find the root cause
   with evidence, then change the minimum necessary.
4. **Small, reviewable changes.** One concern per change. After each task, run
   the app and the tests and confirm nothing is broken before moving on.
5. **Keep scope tight.** Do not add features that are not in the current task.
6. **Ask when ambiguous.** A short question is cheaper than a wrong assumption.

## 5. Architecture conventions

- Standard Django project layout. Group features into focused apps:
  `accounts` (auth, roles, invites), `academics` (terms, courses),
  `folders` (folders, checklist items, files, W/A/B), `review` (review,
  certificates), `reports`.
- Business logic lives in services/model methods, not in views. Views stay thin.
- All uploaded files go to object storage through the storage backend. Never
  serve files from a public bucket; serve via short-lived signed URLs.
- Templates: a base layout + reusable partials. HTMX targets partials.
- Use Django's built-in auth and password hashing. Never store or email a raw
  password; invites use a single-use, expiring set-password link.

## 6. Security rules (apply everywhere)

- Enforce role-based access on the server for every view and object.
- Validate every upload: extension whitelist (pdf, doc, docx, ppt, pptx, xls,
  xlsx, jpg, png), size <= 100 MB, and content-type. Store under
  per-course/per-item keys.
- CSRF protection on, secure cookies, security headers, login rate-limiting and
  lockout, and an audit log of create/update/delete/issue actions.
- Secrets only via environment variables (`django-environ`). Never commit `.env`.

## 7. Commands

```bash
# install
pip install -r requirements.txt

# run (Docker, recommended — matches production)
docker compose up

# run (local)
python manage.py migrate
python manage.py runserver

# tests
pytest

# create the first admin (one-time)
python manage.py createsuperuser
```

## 8. Commit conventions

- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`,
  `chore:`. Imperative mood, concise subject, meaningful body when needed.
- One logical change per commit.
- **Do not mention AI tools, assistants, or code generation in commit messages,
  code comments, or PR descriptions.** Commits read as ordinary professional
  engineering work.

## 9. Design

Use the installed design skills (`ui-ux-pro-max`, `frontend-design`) for the UI.
Target an accessible, calm, professional academic look — not flashy. Consistent
color tokens, clear typography, accessible contrast (WCAG AA), visible focus
states, and `cursor-pointer` on interactive elements. See PLAN.md Phase 10.
