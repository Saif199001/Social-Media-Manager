from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Workspace, WorkspaceMembership
from .permissions import (
    IsActiveWorkspaceMember,
    IsWorkspaceAdminOrOwner,
)
from .serializers import (
    WorkspaceCreateSerializer,
    WorkspaceMembershipSerializer,
    WorkspaceSerializer,
)


class WorkspaceListCreateView(generics.ListCreateAPIView):
    """
    GET:
    Return only Workspaces where the logged-in user
    has an active membership.

    POST:
    Create a Workspace. WorkspaceCreateSerializer uses
    WorkspaceService to automatically create Owner membership.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Workspace.objects.filter(
                memberships__user=self.request.user,
                memberships__status=WorkspaceMembership.Status.ACTIVE,
            )
            .distinct()
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return WorkspaceCreateSerializer

        return WorkspaceSerializer


class WorkspaceDetailView(generics.RetrieveUpdateAPIView):
    """
    GET:
    Active Workspace members can view the Workspace.

    PATCH/PUT:
    Only Owner or Admin can update it.
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(
            memberships__user=self.request.user,
            memberships__status=WorkspaceMembership.Status.ACTIVE,
        ).distinct()

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH"]:
            permission_classes = [
                IsAuthenticated,
                IsWorkspaceAdminOrOwner,
            ]
        else:
            permission_classes = [
                IsAuthenticated,
                IsActiveWorkspaceMember,
            ]

        return [permission() for permission in permission_classes]


class WorkspaceMembersView(generics.ListAPIView):
    """
    Return active members of a Workspace.

    Only an active member of that Workspace can access the list.
    """

    serializer_class = WorkspaceMembershipSerializer
    permission_classes = [
        IsAuthenticated,
        IsActiveWorkspaceMember,
    ]

    def get_workspace(self):
        workspace = generics.get_object_or_404(
            Workspace.objects.filter(
                memberships__user=self.request.user,
                memberships__status=WorkspaceMembership.Status.ACTIVE,
            ).distinct(),
            pk=self.kwargs["workspace_id"],
        )

        self.check_object_permissions(self.request, workspace)

        return workspace

    def get_queryset(self):
        workspace = self.get_workspace()

        return (
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                status=WorkspaceMembership.Status.ACTIVE,
            )
            .select_related("user", "workspace")
            .order_by("joined_at")
        )
