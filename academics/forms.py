"""Forms for academic structure (terms, courses)."""

from django import forms
from django.contrib.auth import get_user_model

from .models import Course, Term

User = get_user_model()

_INPUT = (
    "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "shadow-sm focus:border-gray-900 focus:outline-none focus:ring-1 "
    "focus:ring-gray-900"
)


class TermForm(forms.ModelForm):
    class Meta:
        model = Term
        fields = ("season", "year", "start_date", "end_date", "is_current")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "is_current":
                field.widget.attrs.setdefault(
                    "class", "h-4 w-4 rounded border-gray-300"
                )
            else:
                field.widget.attrs.setdefault("class", _INPUT)

    def clean(self):
        cleaned = super().clean()
        season, year = cleaned.get("season"), cleaned.get("year")
        qs = Term.objects.filter(season=season, year=year)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if season and year and qs.exists():
            raise forms.ValidationError("That term already exists.")
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before the start date.")
        return cleaned


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "code", "title", "section", "program", "study_semester",
            "credit_hours", "instructor", "term",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active faculty can be assigned as instructors.
        self.fields["instructor"].queryset = User.objects.filter(
            role=User.Role.FACULTY, is_active=True
        )
        self.fields["term"].queryset = Term.objects.all()
        if not self.instance.pk and not self.initial.get("term"):
            current = Term.get_current()
            if current:
                self.fields["term"].initial = current.pk

        select_classes = _INPUT
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", select_classes)

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("code")
        section = cleaned.get("section")
        term = cleaned.get("term")
        if code and section and term:
            qs = Course.objects.filter(code=code, section=section, term=term)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "A course with this code and section already exists in that term."
                )
        return cleaned
