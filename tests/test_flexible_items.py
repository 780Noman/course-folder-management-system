"""Flexible add/remove of count-variable items (Task 4)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from academics.models import Course, Term
from folders.models import ChecklistItem, Phase

User = get_user_model()


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


@pytest.mark.django_db
def test_add_assignment_creates_next_numbered_optional_sample_item(faculty_client, course):
    folder = course.folder
    before = folder.items.count()

    resp = faculty_client.post(
        reverse("item_add", args=[course.pk]),
        {"kind": "assignment", "phase": Phase.FINAL},
    )
    assert resp.status_code == 302
    assert folder.items.count() == before + 1

    new = folder.items.order_by("-order").first()
    assert new.title == "Assignment 5 (W,A,B)"   # seed has 1–4
    assert new.is_required is False
    assert new.allows_samples is True
    assert new.is_removable is True
    assert new.phase == Phase.FINAL


@pytest.mark.django_db
def test_add_quiz_into_mid(faculty_client, course):
    faculty_client.post(
        reverse("item_add", args=[course.pk]),
        {"kind": "quiz", "phase": Phase.MID},
    )
    new = course.folder.items.order_by("-order").first()
    assert new.title == "Quizzes- Paper 5 (W,A,B)"
    assert new.phase == Phase.MID


@pytest.mark.django_db
def test_remove_allowed_for_count_variable_item(faculty_client, course):
    assignment4 = course.folder.items.get(order=18)  # Assignment 4, removable
    resp = faculty_client.post(reverse("item_remove", args=[assignment4.pk]))
    assert resp.status_code == 302
    assert not ChecklistItem.objects.filter(pk=assignment4.pk).exists()


@pytest.mark.django_db
def test_core_required_item_cannot_be_removed(faculty_client, course):
    calendar = course.folder.items.get(order=1)  # Academic Calendar, core
    resp = faculty_client.post(reverse("item_remove", args=[calendar.pk]), follow=True)
    assert ChecklistItem.objects.filter(pk=calendar.pk).exists()
    assert b"cannot be removed" in resp.content


@pytest.mark.django_db
def test_other_faculty_cannot_modify_items(client, course):
    other = User.objects.create_user(email="other@uiit.edu.pk", name="Other")
    client.force_login(other)
    resp = client.post(
        reverse("item_add", args=[course.pk]), {"kind": "quiz", "phase": Phase.MID}
    )
    assert resp.status_code == 403


def test_add_requires_post(faculty_client, course):
    assert faculty_client.get(reverse("item_add", args=[course.pk])).status_code == 405
