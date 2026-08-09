from django.contrib import admin

from .models import (
    OAuthState,
    SocialAccount,
    SocialAccountCredential,
)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "platform",
        "account_type",
        "workspace",
        "connection_status",
        "connected_by",
        "last_synced_at",
        "created_at",
    )

    list_filter = (
        "platform",
        "account_type",
        "connection_status",
    )

    search_fields = (
        "display_name",
        "username",
        "platform_account_id",
        "workspace__name",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    raw_id_fields = (
        "workspace",
        "connected_by",
    )


@admin.register(SocialAccountCredential)
class SocialAccountCredentialAdmin(admin.ModelAdmin):
    """
    Credentials are intentionally restricted in Django Admin.
    Token values must never be displayed.
    """

    list_display = (
        "social_account",
        "token_expires_at",
        "refresh_token_expires_at",
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "id",
        "social_account",
        "token_expires_at",
        "refresh_token_expires_at",
        "created_at",
        "updated_at",
    )

    exclude = (
        "encrypted_access_token",
        "encrypted_refresh_token",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OAuthState)
class OAuthStateAdmin(admin.ModelAdmin):
    list_display = (
        "platform",
        "workspace",
        "user",
        "expires_at",
        "consumed_at",
        "created_at",
    )

    list_filter = (
        "platform",
    )

    search_fields = (
        "workspace__name",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "id",
        "workspace",
        "user",
        "platform",
        "state_hash",
        "expires_at",
        "consumed_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False