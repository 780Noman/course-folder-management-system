"""Account models: a custom email-login User with an ADMIN/FACULTY role."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Manager for the email-as-username custom user."""

    use_in_migrations = True

    def _create_user(self, email, name, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        if not name:
            raise ValueError("Users must have a name.")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        # password=None yields an unusable password (used for invited users
        # who set their own password via a one-time link).
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.FACULTY)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, name, password, **extra_fields)

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get("role") != User.Role.ADMIN:
            raise ValueError("Superuser must have role=ADMIN.")
        return self._create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """A faculty member or focal-person (admin). Login is by email."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin (Focal Person)"
        FACULTY = "FACULTY", "Faculty"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.FACULTY)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Whether the user can access the Django admin site.",
    )

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_faculty(self):
        return self.role == self.Role.FACULTY

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name
