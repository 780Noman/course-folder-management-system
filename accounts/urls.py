"""Account / authentication URLs."""

from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("login/", views.RoleLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Change password (logged-in users; the view is login-required)
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url=reverse_lazy("password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html",
        ),
        name="password_change_done",
    ),
    # Password reset (Django built-in views with project templates)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.txt",
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/faculty/", views.faculty_dashboard, name="faculty_dashboard"),
    # Faculty management / invites
    path("manage/faculty/", views.faculty_list, name="faculty_list"),
    path(
        "manage/faculty/<int:pk>/set-active/",
        views.faculty_set_active,
        name="faculty_set_active",
    ),
    path(
        "manage/faculty/<int:pk>/set-password/",
        views.faculty_set_password,
        name="faculty_set_password",
    ),
    path("manage/users/invite/", views.invite_user, name="invite_user"),
    path(
        "invite/<uidb64>/<token>/",
        views.InviteSetPasswordView.as_view(),
        name="invite_confirm",
    ),
]
