from django.urls import path

from .views import (
    WorkspaceDetailView,
    WorkspaceListCreateView,
    WorkspaceMembersView,
)

app_name = "workspaces"

urlpatterns = [
    path(
        "",
        WorkspaceListCreateView.as_view(),
        name="workspace-list-create",
    ),
    path(
        "<uuid:pk>/",
        WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
    path(
        "<uuid:workspace_id>/members/",
        WorkspaceMembersView.as_view(),
        name="workspace-members",
    ),
]