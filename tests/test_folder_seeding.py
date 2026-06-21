"""Course folder is auto-created and seeded from the template (Task 2)."""

import pytest

from academics.models import Course, Term
from folders.models import ChecklistItem, CourseFolder, FolderStatus, ItemStatus
from folders.services import get_or_create_folder


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


@pytest.mark.django_db
def test_folder_created_with_28_items_on_course_creation(course):
    folder = CourseFolder.objects.get(course=course)
    assert folder.status == FolderStatus.DRAFT
    assert folder.items.count() == 28
    assert sorted(folder.items.values_list("order", flat=True)) == list(range(1, 29))


@pytest.mark.django_db
def test_seeded_items_start_pending_and_copy_template_flags(course):
    folder = course.folder
    mid_exam = folder.items.get(order=21)
    assert mid_exam.status == ItemStatus.PENDING
    assert mid_exam.allows_samples is True
    assert mid_exam.phase == "MID"
    projects = folder.items.get(order=25)
    assert projects.is_required is False


@pytest.mark.django_db
def test_get_or_create_folder_is_idempotent(course):
    folder1 = get_or_create_folder(course)
    folder2 = get_or_create_folder(course)
    assert folder1.pk == folder2.pk
    assert ChecklistItem.objects.filter(folder=folder1).count() == 28  # not doubled


@pytest.mark.django_db
def test_each_course_gets_its_own_folder(faculty_user):
    term = Term.objects.create(season=Term.Season.SPRING, year=2026)
    c1 = Course.objects.create(code="CS101", title="A", section="A", program="BSCS",
                               study_semester=1, instructor=faculty_user, term=term)
    c2 = Course.objects.create(code="CS102", title="B", section="A", program="BSCS",
                               study_semester=1, instructor=faculty_user, term=term)
    assert c1.folder.pk != c2.folder.pk
    assert ChecklistItem.objects.count() == 56
