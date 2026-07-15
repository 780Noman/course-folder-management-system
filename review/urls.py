"""Review workflow URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path("courses/<int:course_id>/submit/mid/", views.submit_mid, name="submit_mid"),
    path("courses/<int:course_id>/submit/final/", views.submit_final, name="submit_final"),
    # Admin review
    path("review/", views.review_list, name="review_list"),
    path("review/queue/status/", views.review_queue_status, name="review_queue_status"),
    path("review/<int:course_id>/", views.review_detail, name="review_detail"),
    path("review/<int:course_id>/action/", views.review_action, name="review_action"),
    path("review/<int:course_id>/certify/", views.certify, name="certify"),
    path(
        "courses/<int:course_id>/certificate/",
        views.certificate_download,
        name="certificate_download",
    ),
]
