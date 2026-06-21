"""Reporting queries: course-folder status and missing items, with filters."""

from folders.models import CourseFolder, FolderStatus, ItemStatus

# Report status buckets (the plan's certified / in review / pending).
CERTIFIED = "certified"
IN_REVIEW = "in_review"
PENDING = "pending"

STATUS_BUCKETS = {
    CERTIFIED: (FolderStatus.CERTIFIED,),
    IN_REVIEW: (FolderStatus.MID_SUBMITTED, FolderStatus.FINAL_SUBMITTED),
    PENDING: (
        FolderStatus.DRAFT,
        FolderStatus.MID_APPROVED,
        FolderStatus.FINAL_APPROVED,
    ),
}

STATUS_LABELS = {
    CERTIFIED: "Certified",
    IN_REVIEW: "In review",
    PENDING: "Pending",
}


def report_status(folder_status):
    for bucket, statuses in STATUS_BUCKETS.items():
        if folder_status in statuses:
            return bucket
    return PENDING


def _missing_required(folder):
    """Titles of required, applicable items that are not yet available."""
    return [
        item.title
        for item in folder.items.all()
        if item.is_required
        and item.status != ItemStatus.AVAILABLE
        and item.status != ItemStatus.NOT_APPLICABLE
    ]


def get_report(term_id=None, program=None, instructor_id=None, status=None):
    """Return report rows (one per course folder) honouring the given filters."""
    qs = CourseFolder.objects.select_related(
        "course__instructor", "course__term"
    ).prefetch_related("items")

    if term_id:
        qs = qs.filter(course__term_id=term_id)
    if program:
        qs = qs.filter(course__program=program)
    if instructor_id:
        qs = qs.filter(course__instructor_id=instructor_id)
    if status in STATUS_BUCKETS:
        qs = qs.filter(status__in=STATUS_BUCKETS[status])

    qs = qs.order_by("-course__term__year", "course__term__season", "course__code")

    rows = []
    for folder in qs:
        missing = _missing_required(folder)
        rows.append(
            {
                "folder": folder,
                "course": folder.course,
                "report_status": report_status(folder.status),
                "report_status_label": STATUS_LABELS[report_status(folder.status)],
                "status_display": folder.get_status_display(),
                "missing": missing,
                "missing_count": len(missing),
            }
        )
    return rows


def summarise(rows):
    """Totals per report bucket for the given rows."""
    summary = {CERTIFIED: 0, IN_REVIEW: 0, PENDING: 0}
    for row in rows:
        summary[row["report_status"]] += 1
    return {"labels": STATUS_LABELS, "counts": summary, "total": len(rows)}
