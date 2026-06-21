"""Academic structure: terms and courses."""

from django.conf import settings
from django.db import models


class Term(models.Model):
    """A teaching term, e.g. Spring 2026. Exactly one term is the current one.

    ``name`` from the data model is a derived display value (season + year);
    uniqueness is enforced on (season, year).
    """

    class Season(models.TextChoices):
        SPRING = "SPRING", "Spring"
        SUMMER = "SUMMER", "Summer"
        FALL = "FALL", "Fall"

    season = models.CharField(max_length=10, choices=Season.choices)
    year = models.PositiveIntegerField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)

    # Season ordering for display (Spring -> Summer -> Fall within a year).
    _SEASON_ORDER = {Season.SPRING: 0, Season.SUMMER: 1, Season.FALL: 2}

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["season", "year"], name="uniq_term_season_year"
            ),
        ]
        ordering = ["-year", "season"]

    def __str__(self):
        return self.name

    @property
    def name(self):
        return f"{self.get_season_display()} {self.year}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep a single current term: clear the flag on all others.
        if self.is_current:
            Term.objects.exclude(pk=self.pk).filter(is_current=True).update(
                is_current=False
            )

    @classmethod
    def get_current(cls):
        return cls.objects.filter(is_current=True).first()


class Course(models.Model):
    """One subject taught by one instructor in one term and section.

    A faculty member may have many courses across terms; each is its own row so
    the system keeps full year-by-year history. Uniqueness is (code, section,
    term) so the same subject can recur in later terms.
    """

    title = models.CharField(max_length=200)
    code = models.CharField(max_length=30)
    credit_hours = models.PositiveSmallIntegerField(default=3)
    program = models.CharField(max_length=100, help_text="e.g. BSCS, BSSE, BSIT")
    study_semester = models.PositiveSmallIntegerField(
        help_text="The program semester this course belongs to (1–8)."
    )
    section = models.CharField(max_length=20)

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses",
        limit_choices_to={"role": "FACULTY"},
    )
    term = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="courses"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code", "section", "term"],
                name="uniq_course_code_section_term",
            ),
        ]
        ordering = ["-term__year", "term__season", "code", "section"]

    def __str__(self):
        return f"{self.code} ({self.section}) — {self.title}"
