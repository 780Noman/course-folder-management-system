"""Admin-facing views for managing academic structure."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import admin_required
from audit.services import record

from .forms import CourseForm, TermForm
from .models import Course, Term

User = get_user_model()

# Folder-status buckets mirrored for course search (kept in sync with reports).
_STATUS_FILTERS = {
    "certified": ("CERTIFIED",),
    "in_review": ("MID_SUBMITTED", "FINAL_SUBMITTED"),
    "pending": ("DRAFT", "MID_APPROVED", "FINAL_APPROVED"),
}


@admin_required
def term_list(request):
    """List all terms and create new ones (admin only)."""
    if request.method == "POST":
        form = TermForm(request.POST)
        if form.is_valid():
            term = form.save()
            record(request.user, "term_create", term, name=term.name)
            messages.success(request, f"Term “{term.name}” created.")
            return redirect("term_list")
    else:
        form = TermForm()
    terms = Term.objects.all()
    return render(
        request,
        "academics/term_list.html",
        {"terms": terms, "form": form},
    )


@admin_required
@require_POST
def term_set_current(request, pk):
    """Mark a term as the current one (clears the flag on every other term)."""
    term = get_object_or_404(Term, pk=pk)
    term.is_current = True
    term.save()
    record(request.user, "term_set_current", term, name=term.name)
    messages.success(request, f"“{term.name}” is now the current term.")
    return redirect("term_list")


@admin_required
def course_list(request):
    """List and create courses (admin only). Optional ?term= filter."""
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            record(request.user, "course_create", course,
                   code=course.code, section=course.section, term=course.term_id,
                   instructor=course.instructor_id)
            messages.success(
                request, f"Course “{course.code} ({course.section})” created."
            )
            return redirect("course_list")
    else:
        form = CourseForm()

    courses = Course.objects.select_related("instructor", "term")
    term_filter = request.GET.get("term")
    if term_filter:
        courses = courses.filter(term_id=term_filter)

    return render(
        request,
        "academics/course_list.html",
        {
            "courses": courses,
            "form": form,
            "terms": Term.objects.all(),
            "selected_term": term_filter or "",
        },
    )


def _search_courses(params):
    """Filter courses by query + term/program/faculty/status (admin search)."""
    courses = Course.objects.select_related("instructor", "term", "folder")

    query = (params.get("q") or "").strip()
    if query:
        courses = courses.filter(
            Q(code__icontains=query)
            | Q(title__icontains=query)
            | Q(instructor__name__icontains=query)
        )
    if params.get("term"):
        courses = courses.filter(term_id=params["term"])
    if params.get("program"):
        courses = courses.filter(program=params["program"])
    if params.get("faculty"):
        courses = courses.filter(instructor_id=params["faculty"])
    status = params.get("status")
    if status in _STATUS_FILTERS:
        courses = courses.filter(folder__status__in=_STATUS_FILTERS[status])
    return courses


@admin_required
def course_search(request):
    """Admin search/browse of courses with live (HTMX) results."""
    selected = {
        "q": request.GET.get("q", ""),
        "term": request.GET.get("term", ""),
        "program": request.GET.get("program", ""),
        "faculty": request.GET.get("faculty", ""),
        "status": request.GET.get("status", ""),
    }
    courses = _search_courses(selected)
    context = {
        "courses": courses,
        "selected": selected,
        "terms": Term.objects.all(),
        "programs": sorted(
            p for p in Course.objects.values_list("program", flat=True).distinct() if p
        ),
        "faculty": User.objects.filter(role=User.Role.FACULTY).order_by("name"),
    }
    # HTMX requests get just the results table; full requests get the page.
    if request.htmx:
        return render(request, "academics/_course_search_results.html", context)
    return render(request, "academics/course_search.html", context)
