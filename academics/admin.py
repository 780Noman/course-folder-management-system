from django.contrib import admin

from .models import Course, Term


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "year", "start_date", "end_date", "is_current")
    list_filter = ("season", "year", "is_current")
    ordering = ("-year", "season")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "section", "title", "program", "study_semester",
                    "instructor", "term")
    list_filter = ("term", "program")
    search_fields = ("code", "title", "instructor__name", "instructor__email")
    autocomplete_fields = ("instructor",)
    list_select_related = ("instructor", "term")
