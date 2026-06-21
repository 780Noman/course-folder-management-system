"""The seeded 28-item checklist template (Phase 3, Task 1)."""

import pytest

from folders.models import ChecklistTemplateItem, Phase


@pytest.mark.django_db
def test_exactly_28_items_with_orders_1_to_28():
    qs = ChecklistTemplateItem.objects.all()
    assert qs.count() == 28
    assert sorted(qs.values_list("order", flat=True)) == list(range(1, 29))


@pytest.mark.django_db
def test_phase_distribution():
    counts = {p: ChecklistTemplateItem.objects.filter(phase=p).count()
              for p in (Phase.GENERAL, Phase.MID, Phase.FINAL)}
    assert counts == {Phase.GENERAL: 10, Phase.MID: 7, Phase.FINAL: 11}


@pytest.mark.django_db
def test_sample_items_match_the_official_wab_markings():
    samples = set(
        ChecklistTemplateItem.objects.filter(allows_samples=True)
        .values_list("order", flat=True)
    )
    assert samples == {11, 12, 13, 14, 15, 16, 17, 18, 21, 24}


@pytest.mark.django_db
def test_optional_and_removable_flags():
    optional = set(
        ChecklistTemplateItem.objects.filter(is_required=False)
        .values_list("order", flat=True)
    )
    removable = set(
        ChecklistTemplateItem.objects.filter(is_removable=True)
        .values_list("order", flat=True)
    )
    assert optional == {13, 14, 17, 18, 25}          # quizzes/assign 3-4 + projects
    assert removable == {11, 12, 13, 14, 15, 16, 17, 18}  # quizzes & assignments


@pytest.mark.django_db
def test_known_titles_present_verbatim():
    titles = dict(
        ChecklistTemplateItem.objects.values_list("order", "title")
    )
    assert titles[1] == "Academic Calendar"
    assert titles[5] == "Course Monitoring Form"
    assert titles[21] == "Mid Exam (W,A,B)"
    assert titles[27] == "Final Results (OBE Based)"
    assert titles[28] == "Outcomes Assessment"
