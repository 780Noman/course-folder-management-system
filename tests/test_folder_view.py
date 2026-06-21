"""Faculty folder view: grouping, progress, access control (Task 3)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from academics.models import Course, Term
from folders.models import CourseFolder, ItemStatus

User = get_user_model()


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="Programming", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


def test_owner_can_open_folder(faculty_client, course):
    resp = faculty_client.get(reverse("folder_detail", args=[course.pk]))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "General" in content and "Mid-term" in content and "Final-term" in content


@pytest.mark.django_db
def test_other_faculty_cannot_open_folder(client, course):
    other = User.objects.create_user(
        email="other@uiit.edu.pk", name="Other", password="StrongPass123!"
    )
    client.force_login(other)
    resp = client.get(reverse("folder_detail", args=[course.pk]))
    assert resp.status_code == 403


def test_admin_can_open_any_folder(admin_client, course):
    assert admin_client.get(reverse("folder_detail", args=[course.pk])).status_code == 200


@pytest.mark.django_db
def test_progress_counts_required_available_and_excludes_na(course):
    folder = course.folder
    # General has 10 required items. Mark 2 available, 1 N/A.
    general = list(folder.items.filter(phase="GENERAL"))
    general[0].status = ItemStatus.AVAILABLE
    general[0].save()
    general[1].status = ItemStatus.AVAILABLE
    general[1].save()
    general[2].status = ItemStatus.NOT_APPLICABLE
    general[2].save()

    prog = CourseFolder.progress(folder.items.filter(phase="GENERAL"))
    # 1 item removed from the denominator (N/A), 2 of remaining 9 done.
    assert prog == {"done": 2, "total": 9, "percent": round(2 / 9 * 100)}


@pytest.mark.django_db
def test_opening_folder_for_legacy_course_seeds_it(client, faculty_user):
    """A folder/items are created on first open even if missing."""
    term = Term.objects.create(season=Term.Season.SPRING, year=2026)
    course = Course.objects.create(code="CS200", title="DS", section="A",
                                   program="BSCS", study_semester=3,
                                   instructor=faculty_user, term=term)
    CourseFolder.objects.filter(course=course).delete()  # simulate legacy course
    assert not CourseFolder.objects.filter(course=course).exists()

    client.force_login(faculty_user)
    resp = client.get(reverse("folder_detail", args=[course.pk]))
    assert resp.status_code == 200
    folder = CourseFolder.objects.get(course=course)  # fresh, not the stale cache
    assert folder.items.count() == 28
