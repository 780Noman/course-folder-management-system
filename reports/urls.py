"""Reports URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path("reports/", views.report, name="report"),
    path("reports/export/pdf/", views.report_export_pdf, name="report_export_pdf"),
    path("reports/export/xlsx/", views.report_export_xlsx, name="report_export_xlsx"),
]
