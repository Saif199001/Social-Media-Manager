from rest_framework.permissions import BasePermission

from .models import WorkspaceMembership


class IsActiveWorkspaceMember(BasePermission):
    """
    Allows access only to users who have an active membership
    in the Workspace.
    """

    def has_object_permission(self, request, view, obj):
        return WorkspaceMembership.objects.filter(
            workspace=obj,
            user=request.user,
            status=WorkspaceMembership.Status.ACTIVE,
        ).exists()


class IsWorkspaceAdminOrOwner(BasePermission):
    """
    Allows access only to active Workspace Owners or Admins.
    """

    def has_object_permission(self, request, view, obj):
        return WorkspaceMembership.objects.filter(
            workspace=obj,
            user=request.user,
            status=WorkspaceMembership.Status.ACTIVE,
            role__in=[
                WorkspaceMembership.Role.OWNER,
                WorkspaceMembership.Role.ADMIN,
            ],
        ).exists()


class IsWorkspaceOwner(BasePermission):
    """
    Allows access only to an active Workspace Owner.
    """

    def has_object_permission(self, request, view, obj):
        return WorkspaceMembership.objects.filter(
            workspace=obj,
            user=request.user,
            status=WorkspaceMembership.Status.ACTIVE,
            role=WorkspaceMembership.Role.OWNER,
        ).exists()