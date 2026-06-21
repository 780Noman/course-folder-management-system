"""Review workflow URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path("courses/<int:course_id>/submit/mid/", views.submit_mid, name="submit_mid"),
    path("courses/<int:course_id>/submit/final/", views.submit_final, name="submit_final"),
    # Admin review
    path("review/", views.review_list, name="review_list"),
    path("review/<int:course_id>/", views.review_detail, name="review_detail"),
    path("review/<int:course_id>/action/", views.review_action, name="review_action"),
]
