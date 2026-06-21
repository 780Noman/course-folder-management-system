"""Admin-facing views for managing academic structure."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import admin_required

from .forms import CourseForm, TermForm
from .models import Course, Term


@admin_required
def term_list(request):
    """List all terms and create new ones (admin only)."""
    if request.method == "POST":
        form = TermForm(request.POST)
        if form.is_valid():
            term = form.save()
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
    messages.success(request, f"“{term.name}” is now the current term.")
    return redirect("term_list")


@admin_required
def course_list(request):
    """List and create courses (admin only). Optional ?term= filter."""
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
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
