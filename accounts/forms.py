"""Forms for account management (admin create/change + faculty invites)."""

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User

_WIDGET_CLASSES = (
    "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 "
    "text-sm shadow-sm focus:border-gray-900 focus:outline-none "
    "focus:ring-1 focus:ring-gray-900"
)


class InviteForm(forms.ModelForm):
    """Admin-facing form to create a user with an initial password.

    Built for an offline deployment where no invitation email can be sent: the
    admin sets a starting password and shares it with the user, who can change
    it from their account afterwards. The password is validated against the
    project's password policy and is never emailed or written to the log.
    """

    password = forms.CharField(
        label="Initial password",
        # Visible (not masked) so the admin can read it back and pass it on.
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
        help_text="Share this with the user. They can change it after signing in.",
    )

    class Meta:
        model = User
        fields = ("name", "email", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", _WIDGET_CLASSES)

    def clean_email(self):
        # Stored and compared case-insensitively to avoid duplicate accounts.
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        if password:
            # Validate here (not clean_password) so the throwaway user carries
            # the already-cleaned name/email for the similarity check, whatever
            # order the fields were cleaned in.
            candidate = User(
                email=cleaned.get("email", ""), name=cleaned.get("name", "")
            )
            try:
                password_validation.validate_password(password, candidate)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return cleaned


class SetUserPasswordForm(forms.Form):
    """Admin sets/resets an existing user's password (offline password recovery).

    Mirrors the invite password field: validated against the password policy,
    shown so the admin can share it, never logged.
    """

    password = forms.CharField(
        label="New password",
        widget=forms.TextInput(attrs={"autocomplete": "off", "class": _WIDGET_CLASSES}),
        help_text="Share this with the user. They can change it after signing in.",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        password_validation.validate_password(password, self.user)
        return password


class AdminUserCreationForm(UserCreationForm):
    """Create-user form used in the Django admin (sets a password directly)."""

    class Meta:
        model = User
        fields = ("email", "name", "role")
        field_classes = {"email": forms.EmailField}


class AdminUserChangeForm(UserChangeForm):
    """Change-user form used in the Django admin."""

    class Meta:
        model = User
        fields = ("email", "name", "role", "is_active", "is_staff",
                  "is_superuser", "groups", "user_permissions")
