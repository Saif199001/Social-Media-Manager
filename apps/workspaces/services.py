from django.db import transaction
from django.utils.text import slugify

from .models import Workspace, WorkspaceMembership


class WorkspaceService:
    """
    Business logic related to Workspace creation and management.
    """

    @staticmethod
    @transaction.atomic
    def create_workspace(
        *,
        user,
        name,
        slug=None,
        logo=None,
        website=None,
        timezone="Asia/Kolkata",
        country_code=None,
        currency=None,
    ):
        """
        Create a Workspace and automatically make the creator
        the Owner of that Workspace.

        Both operations run inside one database transaction.
        """

        if slug:
            workspace_slug = slugify(slug)
        else:
            workspace_slug = slugify(name)

        workspace = Workspace.objects.create(
            name=name,
            slug=workspace_slug,
            logo=logo,
            website=website,
            timezone=timezone,
            country_code=country_code.upper() if country_code else None,
            currency=currency.upper() if currency else None,
            created_by=user,
        )

        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=user,
            role=WorkspaceMembership.Role.OWNER,
            status=WorkspaceMembership.Status.ACTIVE,
        )

        return workspace