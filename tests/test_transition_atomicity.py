"""Review transitions are atomic: a failure mid-transition leaves no partial
state, and a repeated transition fails its guard instead of applying twice."""

import pytest

from academics.models import Course, Term
from folders.models import FolderStatus, ItemStatus
from review import services


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


def _complete_phases(folder, phases):
    folder.items.filter(phase__in=phases, is_required=True).update(
        status=ItemStatus.AVAILABLE
    )


@pytest.mark.django_db
def test_second_submit_fails_cleanly(course, faculty_user):
    from folders.models import CourseFolder

    folder = course.folder
    _complete_phases(folder, CourseFolder.MID_PHASES)

    services.submit_mid(folder, faculty_user)
    assert folder.status == FolderStatus.MID_SUBMITTED  # caller instance synced

    with pytest.raises(services.TransitionError):
        services.submit_mid(folder, faculty_user)  # double-click / second tab


@pytest.mark.django_db
def test_failed_transition_rolls_back_completely(course, faculty_user, admin_user, monkeypatch):
    """If the audit write (last step) fails, the status change and flag
    updates must roll back with it."""
    from folders.models import CourseFolder

    folder = course.folder
    _complete_phases(folder, CourseFolder.MID_PHASES)
    services.submit_mid(folder, faculty_user)

    def _boom(*args, **kwargs):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr(services, "record", _boom)
    with pytest.raises(RuntimeError):
        services.approve_mid(folder, admin_user)

    folder.refresh_from_db()
    assert folder.status == FolderStatus.MID_SUBMITTED  # unchanged
    assert folder.mid_approved_at is None

    # Retry succeeds once the hiccup is gone.
    monkeypatch.undo()
    services.approve_mid(folder, admin_user)
    assert folder.status == FolderStatus.MID_APPROVED


@pytest.mark.django_db
def test_return_rolls_back_flags_with_status(course, faculty_user, admin_user, monkeypatch):
    """A crash between flagging items and saving the folder status must not
    leave items flagged while the folder still shows MID_SUBMITTED."""
    from folders.models import CourseFolder

    folder = course.folder
    _complete_phases(folder, CourseFolder.MID_PHASES)
    services.submit_mid(folder, faculty_user)

    item = folder.items.filter(phase__in=CourseFolder.MID_PHASES).first()

    monkeypatch.setattr(services, "record", lambda *a, **k: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        services.return_mid(
            folder, admin_user, overall_note="fix", flagged_notes={item.id: "redo"}
        )

    item.refresh_from_db()
    folder.refresh_from_db()
    assert item.is_flagged is False  # rolled back with the status
    assert folder.status == FolderStatus.MID_SUBMITTED
