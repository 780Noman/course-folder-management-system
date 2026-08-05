"""Academic structure URLs (admin term/course management)."""

from django.urls import path

from . import views

urlpatterns = [
    path("manage/terms/", views.term_list, name="term_list"),
    path("manage/terms/<int:pk>/edit/", views.term_edit, name="term_edit"),
    path(
        "manage/terms/<int:pk>/set-current/",
        views.term_set_current,
        name="term_set_current",
    ),
    path("manage/courses/", views.course_list, name="course_list"),
    path("manage/courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/search/", views.course_search, name="course_search"),
]
