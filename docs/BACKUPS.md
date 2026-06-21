# Backups & Restore

The system holds two kinds of state that must be backed up independently:

1. **PostgreSQL database** — users, terms, courses, folders, checklist items,
   review state, certificates metadata, and the audit log.
2. **Object storage (Cloudflare R2 / S3)** — all uploaded files, image
   thumbnails, and generated certificate PDFs (private bucket).

A restore is only valid if the database snapshot and the bucket contents are from
about the same time, because `ItemFile` / `Certificate` rows reference storage keys.

---

## 1. PostgreSQL

### Managed provider (recommended)

If the database is hosted on a managed provider (Render, Railway, Neon, RDS,
etc.), enable the provider's **automated daily snapshots** with **point-in-time
recovery** and a retention of at least **14 days**. This is the primary backup.

### Self-managed / extra logical backup

Schedule a nightly logical dump as a second line of defence. Example cron
(adjust credentials via environment, never hard-code):

```bash
# 02:30 every day — compressed custom-format dump, 14-day retention
30 2 * * *  pg_dump "$DATABASE_URL" -Fc -f "/backups/db/coursefolders-$(date +\%F).dump" \
            && find /backups/db -name 'coursefolders-*.dump' -mtime +14 -delete
```

Push the dump off-box (to R2/S3, a different bucket than uploads) so a single host
loss does not lose both the app and its backups.

### Restore

```bash
# new/empty database
createdb coursefolders
pg_restore --clean --if-exists -d "$DATABASE_URL" coursefolders-YYYY-MM-DD.dump
python manage.py migrate            # ensure schema is current
```

---

## 2. Object storage (R2 / S3)

Uploads and certificates live under `course/<id>/item/<id>/...` and
`course/<id>/certificate/...` keys in a **private** bucket.

### Protection

- **Enable bucket versioning** so overwritten/deleted objects are recoverable.
- **Enable lifecycle rules**: keep non-current versions ~30 days; optionally
  transition old versions to cheaper storage.
- **Cross-bucket/region replication** (or a scheduled `rclone`/`aws s3 sync` to a
  separate backup bucket) for disaster recovery:

```bash
# nightly mirror to a backup bucket (R2/S3 compatible)
0 3 * * *  rclone sync r2:coursefolders-prod r2:coursefolders-backup --fast-list
```

### Restore

Restore (or `rclone copy`) the objects back to the production bucket, then restore
the matching database snapshot from the same date so keys line up.

---

## 3. Schedule & ownership summary

| What | Mechanism | Frequency | Retention |
|------|-----------|-----------|-----------|
| Database | Managed snapshots + PITR | continuous / daily | ≥ 14 days |
| Database | `pg_dump` to backup bucket | nightly | 14 days |
| Object storage | Bucket versioning | continuous | 30 days |
| Object storage | `rclone sync` to backup bucket | nightly | 30 days |

- **Test restores quarterly** into a scratch environment — an untested backup is
  not a backup.
- Store all credentials in environment variables / the host's secret manager;
  never commit them. Backup buckets must also be **private**.
- Secrets themselves (`.env`) are not backed up here — keep them in the secret
  manager so a restore can re-supply them.
