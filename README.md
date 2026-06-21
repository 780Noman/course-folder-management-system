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

```bash
cp .env.example .env      # fill in values
docker compose up         # app at http://localhost:8000
```
