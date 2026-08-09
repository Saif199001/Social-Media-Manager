import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.social_accounts.models import OAuthState


class InvalidOAuthState(Exception):
    """Raised when an OAuth state is invalid, expired, or already used."""


class OAuthStateService:
    STATE_TTL_MINUTES = 10

    @staticmethod
    def _hash_state(raw_state: str) -> str:
        return hashlib.sha256(raw_state.encode("utf-8")).hexdigest()

    @classmethod
    def create_state(cls, *, user, workspace, platform) -> str:
        """
        Create a short-lived OAuth state.

        Returns the raw state that can be sent to the OAuth provider.
        Only its SHA-256 hash is stored in the database.
        """

        raw_state = secrets.token_urlsafe(48)
        state_hash = cls._hash_state(raw_state)

        OAuthState.objects.create(
            user=user,
            workspace=workspace,
            platform=platform,
            state_hash=state_hash,
            expires_at=timezone.now()
            + timedelta(minutes=cls.STATE_TTL_MINUTES),
        )

        return raw_state

    @classmethod
    @transaction.atomic
    def consume_state(cls, *, raw_state: str) -> OAuthState:
        """
        Validate and consume an OAuth state exactly once.
        """

        state_hash = cls._hash_state(raw_state)

        try:
            oauth_state = (
                OAuthState.objects
                .select_for_update()
                .select_related("user", "workspace")
                .get(state_hash=state_hash)
            )
        except OAuthState.DoesNotExist as exc:
            raise InvalidOAuthState("Invalid OAuth state.") from exc

        if oauth_state.consumed_at is not None:
            raise InvalidOAuthState(
                "OAuth state has already been used."
            )

        if oauth_state.expires_at <= timezone.now():
            raise InvalidOAuthState(
                "OAuth state has expired."
            )

        oauth_state.consumed_at = timezone.now()

        oauth_state.save(
            update_fields=["consumed_at"]
        )

        return oauth_state

