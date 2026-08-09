from rest_framework import serializers

from .models import Workspace, WorkspaceMembership
from .services import WorkspaceService


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = [
            "id",
            "user_id",
            "username",
            "email",
            "role",
            "status",
            "joined_at",
        ]
        read_only_fields = fields


class WorkspaceSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "slug",
            "logo",
            "website",
            "timezone",
            "country_code",
            "currency",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]


class WorkspaceCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Workspace
        fields = [
            "name",
            "slug",
            "logo",
            "website",
            "timezone",
            "country_code",
            "currency",
        ]

        extra_kwargs = {
            "slug": {
                "required": False,
                "allow_blank": True,
            },
            "logo": {
                "required": False,
                "allow_null": True,
            },
            "website": {
                "required": False,
                "allow_null": True,
            },
            "timezone": {
                "required": False,
            },
            "country_code": {
                "required": False,
                "allow_null": True,
            },
            "currency": {
                "required": False,
                "allow_null": True,
            },
        }

    def create(self, validated_data):
        request = self.context["request"]

        return WorkspaceService.create_workspace(
            user=request.user,
            **validated_data,
        )