"""Admin oversight reports (on-screen, PDF, Excel)."""

from io import BytesIO

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from academics.models import Course, Term
from accounts.permissions import admin_required
from review.pdf import PdfRenderError, render_pdf

from .services import get_report, summarise

User = get_user_model()


def _filters(request):
    return {
        "term_id": request.GET.get("term") or None,
        "program": request.GET.get("program") or None,
        "instructor_id": request.GET.get("faculty") or None,
        "status": request.GET.get("status") or None,
    }


def _filter_options():
    return {
        "terms": Term.objects.all(),
        "programs": sorted(
            p for p in Course.objects.values_list("program", flat=True).distinct() if p
        ),
        "faculty": User.objects.filter(role=User.Role.FACULTY).order_by("name"),
    }


@admin_required
def report(request):
    filters = _filters(request)
    rows = get_report(**filters)
    context = {
        "rows": rows,
        "summary": summarise(rows),
        "options": _filter_options(),
        "selected": filters,
    }
    return render(request, "reports/report.html", context)


@admin_required
def report_export_pdf(request):
    filters = _filters(request)
    rows = get_report(**filters)
    html = render_to_string(
        "reports/report_pdf.html",
        {"rows": rows, "summary": summarise(rows), "generated_at": timezone.now()},
    )
    try:
        pdf = render_pdf(html)
    except PdfRenderError:
        messages.error(
            request,
            "The PDF export could not be generated. Please try again; if it "
            "keeps failing, check the server log.",
        )
        return redirect("report")
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="course-folder-report.pdf"'
    return response


@admin_required
def report_export_xlsx(request):
    from openpyxl import Workbook

    filters = _filters(request)
    rows = get_report(**filters)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Course folders"
    sheet.append([
        "Course", "Section", "Title", "Instructor", "Term", "Program",
        "Semester", "Status", "Missing count", "Missing items",
    ])
    for row in rows:
        course = row["course"]
        sheet.append([
            course.code, course.section, course.title, course.instructor.name,
            course.term.name, course.program, course.study_semester,
            row["report_status_label"], row["missing_count"],
            "; ".join(row["missing"]),
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="course-folder-report.xlsx"'
    return response
