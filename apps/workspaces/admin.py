from django.contrib import admin

from .models import Workspace, WorkspaceMembership


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "status",
        "timezone",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "timezone",
    )

    search_fields = (
        "name",
        "slug",
        "created_by__username",
        "created_by__email",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "workspace",
        "role",
        "status",
        "joined_at",
    )

    list_filter = (
        "role",
        "status",
    )

    search_fields = (
        "user__username",
        "user__email",
        "workspace__name",
    )

    readonly_fields = (
        "id",
        "joined_at",
        "created_at",
        "updated_at",
    )
