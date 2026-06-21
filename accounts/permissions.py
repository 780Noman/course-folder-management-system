"""Server-side role enforcement: decorators (FBV) and mixins (CBV).

A logged-out user is redirected to the login page; a logged-in user with the
wrong role gets a hard 403 (PermissionDenied) rather than a login redirect, so
access control never silently leaks a different role's pages.
"""

from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import User


def _role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if user.role != required_role:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


admin_required = _role_required(User.Role.ADMIN)
faculty_required = _role_required(User.Role.FACULTY)


class RoleRequiredMixin(LoginRequiredMixin):
    """Base CBV mixin: require login and a specific role."""

    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != self.required_role:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    required_role = User.Role.ADMIN


class FacultyRequiredMixin(RoleRequiredMixin):
    required_role = User.Role.FACULTY
