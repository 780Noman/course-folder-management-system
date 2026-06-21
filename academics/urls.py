"""Academic structure URLs (admin term/course management)."""

from django.urls import path

from . import views

urlpatterns = [
    path("manage/terms/", views.term_list, name="term_list"),
    path(
        "manage/terms/<int:pk>/set-current/",
        views.term_set_current,
        name="term_set_current",
    ),
    path("manage/courses/", views.course_list, name="course_list"),
    path("courses/search/", views.course_search, name="course_search"),
]
