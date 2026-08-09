import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validate_timezone(value):
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        raise ValidationError("Enter a valid timezone, for example Asia/Kolkata.")


def validate_currency(value):
    if value and (len(value) != 3 or not value.isalpha()):
        raise ValidationError("Currency must be a 3-letter code, for example INR.")


class Workspace(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(max_length=150)

    slug = models.SlugField(
        max_length=160,
        unique=True,
    )

    logo = models.URLField(
        blank=True,
        null=True,
    )

    website = models.URLField(
        blank=True,
        null=True,
    )

    timezone = models.CharField(
        max_length=64,
        default="Asia/Kolkata",
        validators=[validate_timezone],
    )

    country_code = models.CharField(
        max_length=2,
        blank=True,
        null=True,
    )

    currency = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        validators=[validate_currency],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_workspaces",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class WorkspaceMembership(models.Model):

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        VIEWER = "viewer", "Viewer"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"],
                name="unique_workspace_user_membership",
            )
        ]

        indexes = [
            models.Index(
                fields=["user", "status"],
                name="ws_member_user_status_idx",
            ),
            models.Index(
                fields=["workspace", "role"],
                name="ws_member_ws_role_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.workspace} ({self.role})"