# Data Model

This is the source of truth for the database schema. Update it whenever the
schema changes.

## Entities and relationships (overview)

```
User (Django auth, custom)
  └─ role: ADMIN | FACULTY

Term            (Spring 2026, Fall 2026, Summer 2026, ...)
  └─ has many Courses

Course          (one row per subject taught, per term, per section)
  ├─ instructor -> User (FACULTY)
  ├─ term -> Term
  └─ has one CourseFolder

CourseFolder    (the checklist container for one Course)
  ├─ status: DRAFT | MID_SUBMITTED | MID_APPROVED | FINAL_SUBMITTED | CERTIFIED
  └─ has many ChecklistItems

ChecklistItem   (one required/optional line of the checklist)
  ├─ phase: GENERAL | MID | FINAL
  ├─ is_required: bool
  ├─ status: PENDING | AVAILABLE | NOT_APPLICABLE
  ├─ na_note: text (optional, when NOT_APPLICABLE)
  └─ has many ItemFiles (optionally grouped by W/A/B)

ItemFile        (an uploaded file in object storage)
  ├─ sample_kind: NONE | WORST | AVERAGE | BEST
  ├─ file key + original name + size + content type
  └─ thumbnail key (for images)

Certificate     (generated PDF, one per CourseFolder)
  ├─ issued_by -> User (ADMIN)
  └─ issued_at, pdf key

AuditLog        (who did what, when)
ChecklistTemplateItem (the default 28 items used to seed a new folder)
```

## Why courses are tied to a Term

A faculty member may teach several subjects at once (morning/evening, different
programs and study-semesters). Each is its own `Course` row linked to one
`Term`. Past terms are never deleted, so the system keeps full year-by-year
history. Faculty default to the current term and can switch to view older terms;
admin can filter across all terms.

## The two-phase checklist (Mid / Final)

The official checklist mixes mid-term and final-term material, and folders are
submitted after the mid-term and again about a week after the final term. So
each `ChecklistItem` has a `phase`:

- **GENERAL** — setup items present from the start (academic calendar,
  timetable, grading model, marks distribution).
- **MID** — mid-term material (mid question paper, mid solution, mid exam W/A/B,
  early quizzes/assignments).
- **FINAL** — final material (final exam paper/solution W/A/B, final results,
  outcomes assessment, projects).

Faculty complete and submit the **Mid** items after the mid-term; the admin can
review and approve that phase without final items blocking it. After the final
term, faculty complete the **Final** items and submit again.

**One certificate per course** is issued only when every *required and
applicable* item across both phases is `AVAILABLE` and the admin approves.

## Flexible items

The default 28-item checklist is seeded from `ChecklistTemplateItem` when a
folder is created, but faculty can:

- add or remove count-variable items (e.g. Assignment 3, Assignment 4) to match
  the course's credit hours,
- add/remove W/A/B sample slots on an item,
- mark an item `NOT_APPLICABLE` with an optional note (e.g. "no project this
  semester"). N/A items are skipped by the completeness check.

Core required items cannot be removed; this preserves the rule that no
certificate is issued while a required item is missing.

## Key fields per entity (starting point — refine in Phase 2/3)

**User:** name, email (unique, used for login + invite), role, is_active.

**Term:** name, season (SPRING|FALL|SUMMER), year, start_date, end_date,
is_current.

**Course:** title, code, credit_hours, program, study_semester, section,
instructor (FK), term (FK). Unique together: (code, section, term).

**CourseFolder:** course (OneToOne), status, mid_submitted_at,
mid_approved_at, final_submitted_at, certified_at.

**ChecklistItem:** folder (FK), title, phase, is_required, order,
allows_samples (bool, for W/A/B), status, na_note.

**ItemFile:** item (FK), sample_kind, file (storage key), original_name,
size_bytes, content_type, thumbnail (nullable), uploaded_by, uploaded_at.

**Certificate:** folder (OneToOne), pdf (storage key), issued_by, issued_at.

**AuditLog:** actor (FK), action, target_type, target_id, metadata (json),
created_at.
