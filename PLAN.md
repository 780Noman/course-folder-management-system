# Build Plan — Course Folder Management System

End-to-end plan. Work **one phase at a time, one task at a time**, in order.
After every task: run the app, run `pytest`, confirm nothing broke, commit.
Do not start a phase until the previous phase's acceptance checks pass.

Read `CLAUDE.md` and `docs/DATA_MODEL.md` before starting.

---

## Phase 0 — Project setup

**Goal:** a running, empty Django project with the right tooling.

Tasks:
1. Create the Django project `config/` and confirm `python manage.py runserver`
   serves the default page.
2. Wire `django-environ`; load all settings from environment (see `.env.example`).
3. Split settings into `base`, `dev`, `prod`.
4. Configure PostgreSQL via env. Confirm `migrate` runs.
5. Add WhiteNoise, Gunicorn, `django-htmx`, Tailwind build, base template.
6. Add `pytest.ini`, write one trivial passing test.
7. Confirm `docker compose up` runs the app + Postgres.

**Acceptance:** app runs in Docker and locally; tests pass; no secrets in code.

---

## Phase 1 — Accounts, roles, and login

**Goal:** secure auth with two roles and the invite flow.

Tasks:
1. Custom `User` (email login, `role` = ADMIN|FACULTY, name).
2. Single login page; redirect by role to the correct dashboard.
3. Server-side role enforcement (decorators/mixins). Add tests proving a faculty
   user cannot reach admin views and vice-versa.
4. Invite flow: admin creates a user by name+email; system emails a single-use,
   expiring set-password link; the user sets their own password. No raw password
   is ever stored or emailed.
5. Password reset, login rate-limiting, and lockout.
6. `manage.py createsuperuser` documented as the one-time first-admin step.

**Acceptance:** admin and faculty can be created and log in; roles are enforced
server-side; invite + reset flows work; tests cover access control.

---

## Phase 2 — Terms, courses, faculty

**Goal:** the academic structure with full multi-term history.

Tasks:
1. `Term` model + admin screen to create terms and mark the current one.
2. `Course` model tied to instructor + term; admin can create/assign courses.
3. Faculty management screens for admin (add/remove faculty, list, search).
4. Faculty dashboard: list own courses for the current term, with a term switch
   to view past terms.

**Acceptance:** a faculty member with multiple courses across terms sees them
correctly; past terms remain visible; admin can manage faculty and courses.

---

## Phase 3 — Course folder + checklist (two-phase)

**Goal:** the folder with its seeded, flexible, phased checklist.

Tasks:
1. `ChecklistTemplateItem` seeded with the official 28 items, each tagged
   GENERAL/MID/FINAL, required/optional, and allows_samples where applicable.
2. On course creation (or first open), create a `CourseFolder` and seed its
   `ChecklistItem`s from the template.
3. Faculty folder view grouped into **Mid-term** and **Final-term** sections
   with per-section progress.
4. Flexible items: add/remove count-variable items; cannot remove core required
   items.
5. Mark item `NOT_APPLICABLE` with optional note; excluded from completeness.

**Acceptance:** opening a course shows the seeded two-phase checklist; flexibility
and N/A behave per `docs/DATA_MODEL.md`; completeness ignores N/A items.

---

## Phase 4 — File uploads, storage, thumbnails

**Goal:** reliable, secure, fast file handling.

Tasks:
1. Configure `django-storages` + `boto3` against the object store (R2/S3). All
   uploads go to private storage under `course/<id>/item/<id>/...` keys.
2. Upload validation: extension whitelist, <= 50 MB, content-type check.
3. Generate image thumbnails with Pillow on upload.
4. Folder view lists files / thumbnails only; the full file loads **on click**
   via a short-lived signed URL (lazy, not all at once).
5. Edit/delete own files (faculty); deletes remove the storage object too.

**Acceptance:** uploads validate and persist to object storage; dashboards stay
light (thumbnails only); full files open on demand via signed URLs.

---

## Phase 5 — W/A/B samples

**Goal:** Worst/Average/Best sub-grouping on relevant items.

Tasks:
1. On `allows_samples` items, group files under WORST / AVERAGE / BEST.
2. Add/remove sample slots; upload into a specific sample group.
3. Completeness logic accounts for required sample groups.

**Acceptance:** sample items show three groups, accept files per group, and count
correctly toward completeness.

---

## Phase 6 — Review + red highlighting

**Goal:** the admin review and revision loop.

Tasks:
1. Faculty "Submit mid-term" / "Submit final" actions (only when that phase's
   required items are complete).
2. Admin review screen for a folder: missing/incomplete items highlighted in
   **red**; per-phase status.
3. Admin can approve a phase or return it with notes; faculty sees what is
   missing and re-submits.
4. Record every action in the audit log.

**Acceptance:** the submit -> review -> return/approve loop works; missing items
are clearly flagged; actions are audited.

---

## Phase 7 — Certificate generation

**Goal:** the Course Folder Review Certificate PDF.

Tasks:
1. HTML certificate template matching the official format (university header,
   course metadata, item table with availability, instructor + focal-person
   lines).
2. Generate the PDF with WeasyPrint when both phases are approved and every
   required+applicable item is AVAILABLE.
3. Block issuance if anything required is missing; store the PDF in object
   storage; let admin issue and faculty download.

**Acceptance:** a complete folder produces a correct certificate PDF; an
incomplete one cannot be certified.

---

## Phase 8 — Admin reports

**Goal:** oversight reporting.

Tasks:
1. Report view: per term/program, which courses are certified, in review, or
   pending, and what is missing.
2. Filters (term, program, faculty, status) and on-screen table.
3. Export to PDF and Excel (xlsx).

**Acceptance:** admin can produce an accurate certified/pending report and export
it.

---

## Phase 9 — Search and filtering

**Goal:** find things fast across the system.

Tasks:
1. Admin: filter by term/program/faculty/status; search by faculty name or
   course code (HTMX live results).
2. Faculty: filter own courses by term; search.

**Acceptance:** filters and search return correct results without full page
reloads.

---

## Phase 10 — Design system pass

**Goal:** a cohesive, accessible, professional UI.

Tasks:
1. Use `ui-ux-pro-max` to generate a design system (the Accessible & Ethical /
   education direction): color tokens, typography pairing, components. Persist it
   to `design-system/MASTER.md`.
2. Apply tokens across base layout, dashboards, folder view, review, and
   certificate.
3. Apply `frontend-design` guidance: spacing, states, focus rings, reduced-motion,
   responsive breakpoints (375 / 768 / 1024 / 1440).

**Acceptance:** consistent tokens everywhere; WCAG AA contrast; visible focus;
responsive; no templated-default look.

---

## Phase 11 — Security hardening

**Goal:** production-grade safety.

Tasks:
1. Re-audit role enforcement on every view and object.
2. Confirm private storage + signed URLs only; no public file links.
3. Security headers, secure cookies, CSRF, rate-limiting/lockout verified.
4. Audit log coverage for create/update/delete/issue.
5. Backups: scheduled database + object-storage backups documented.
6. Dependency check; pin and update known-vulnerable packages.

**Acceptance:** access control holds under tests; no public file exposure; headers
and backups in place.

---

## Phase 12 — Deployment

**Goal:** live on the cloud.

Tasks:
1. Production Docker image; `collectstatic`; Gunicorn config.
2. Deploy to the chosen host (Render or Railway, or Hetzner + own Coolify);
   managed PostgreSQL; environment variables set.
3. Object storage (Cloudflare R2) bucket + credentials; email provider (SMTP or
   Brevo).
4. HTTPS, custom domain, first-admin invite, smoke test of every role flow.

**Acceptance:** the system is reachable over HTTPS; all role flows work in
production; the first admin can onboard faculty.

---

## Out of scope for v1 (note for later)

- Separate React SPA / public API (HTMX covers v1 interactivity).
- SSO with the university identity provider (app-managed invites for now).
- Async task queue (emails/thumbnails are synchronous in v1; add Celery/django-q
  later if volume grows).
