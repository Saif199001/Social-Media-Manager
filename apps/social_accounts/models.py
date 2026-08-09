import uuid

from django.conf import settings
from django.db import models


class SocialAccount(models.Model):

    class Platform(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        LINKEDIN = "linkedin", "LinkedIn"
        YOUTUBE = "youtube", "YouTube"
        X = "x", "X"

    class AccountType(models.TextChoices):
        PAGE = "page", "Page"
        BUSINESS = "business", "Business"
        CREATOR = "creator", "Creator"
        CHANNEL = "channel", "Channel"
        PROFILE = "profile", "Profile"
        ORGANIZATION = "organization", "Organization"
        OTHER = "other", "Other"

    class ConnectionStatus(models.TextChoices):
        CONNECTED = "connected", "Connected"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"
        ERROR = "error", "Error"
        DISCONNECTED = "disconnected", "Disconnected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )

    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
    )

    platform_account_id = models.CharField(
        max_length=255,
    )

    account_type = models.CharField(
        max_length=30,
        choices=AccountType.choices,
        default=AccountType.OTHER,
    )

    display_name = models.CharField(
        max_length=255,
    )

    username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    avatar_url = models.URLField(
        blank=True,
        null=True,
    )

    connection_status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.CONNECTED,
    )

    scopes = models.JSONField(
        default=list,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    last_synced_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="connected_social_accounts",
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
                fields=[
                    "workspace",
                    "platform",
                    "platform_account_id",
                ],
                name="unique_social_account_per_workspace",
            ),
        ]

        indexes = [
            models.Index(
                fields=["workspace", "platform"],
            ),
            models.Index(
                fields=["workspace", "connection_status"],
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.platform})"


class SocialAccountCredential(models.Model):
    """
    Stores protected OAuth credentials separately from SocialAccount.

    IMPORTANT:
    Token values stored in these fields must be encrypted
    before being saved. Plaintext token storage is not allowed.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    social_account = models.OneToOneField(
        SocialAccount,
        on_delete=models.CASCADE,
        related_name="credential",
    )

    encrypted_access_token = models.TextField()

    encrypted_refresh_token = models.TextField(
        blank=True,
        null=True,
    )

    token_expires_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    refresh_token_expires_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Credential for {self.social_account}"


class OAuthState(models.Model):
    """
    Short-lived, one-time OAuth state.

    Binds an OAuth authorization attempt to:
    - authenticated user
    - workspace
    - provider/platform
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="oauth_states",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_states",
    )

    platform = models.CharField(
        max_length=20,
        choices=SocialAccount.Platform.choices,
    )

    state_hash = models.CharField(
        max_length=128,
        unique=True,
    )

    expires_at = models.DateTimeField()

    consumed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["workspace", "platform"],
            ),
            models.Index(
                fields=["expires_at"],
            ),
        ]

    def __str__(self):
        return f"{self.platform} OAuth state"