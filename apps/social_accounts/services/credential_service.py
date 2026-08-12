from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from apps.social_accounts.models import (
    SocialAccount,
    SocialAccountCredential,
)


class CredentialService:
    """
    Generic credential encryption and persistence service.

    This service is provider-agnostic.
    It does not contain Facebook, Instagram, LinkedIn,
    X, YouTube, or any other platform-specific logic.
    """

    # ==========================================================
    # ENCRYPTION
    # ==========================================================

    @staticmethod
    def _get_fernet():
        """
        Create a Fernet instance using the application-level
        encryption key from Django settings.
        """

        encryption_key = getattr(
            settings,
            "SOCIAL_ACCOUNT_ENCRYPTION_KEY",
            None,
        )

        if not encryption_key:
            raise RuntimeError(
                "SOCIAL_ACCOUNT_ENCRYPTION_KEY is not configured."
            )

        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode("utf-8")

        try:
            return Fernet(encryption_key)
        except Exception as exc:
            raise RuntimeError(
                "Invalid SOCIAL_ACCOUNT_ENCRYPTION_KEY."
            ) from exc

    @classmethod
    def encrypt(cls, value):
        """
        Encrypt a plaintext credential/token.

        Returns:
            str | None
        """

        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        if value == "":
            return None

        fernet = cls._get_fernet()

        return fernet.encrypt(
            value.encode("utf-8")
        ).decode("utf-8")

    @classmethod
    def decrypt(cls, encrypted_value):
        """
        Decrypt an encrypted credential/token.

        Returns:
            str | None
        """

        if encrypted_value is None:
            return None

        if not isinstance(encrypted_value, str):
            encrypted_value = str(encrypted_value)

        if encrypted_value == "":
            return None

        fernet = cls._get_fernet()

        try:
            return fernet.decrypt(
                encrypted_value.encode("utf-8")
            ).decode("utf-8")

        except InvalidToken as exc:
            raise RuntimeError(
                "Unable to decrypt social account credential."
            ) from exc

    # ==========================================================
    # SAVE
    # ==========================================================

    @classmethod
    def save_credentials(
        cls,
        *,
        social_account,
        access_token,
        refresh_token=None,
        token_expires_at=None,
        refresh_token_expires_at=None,
    ):
        """
        Encrypt and persist OAuth credentials.

        This method is provider-agnostic.

        access_token:
            Required platform access token.

        refresh_token:
            Optional refresh token. Providers such as Facebook
            may not provide a conventional refresh token.

        Existing refresh credentials are preserved when the
        caller does not provide a new refresh token.
        """

        if not isinstance(social_account, SocialAccount):
            raise ValueError(
                "social_account must be a SocialAccount instance."
            )

        if not access_token:
            raise ValueError(
                "access_token is required."
            )

        encrypted_access_token = cls.encrypt(
            access_token
        )

        # Get existing credential first so an omitted refresh
        # token does not accidentally erase an existing one.
        credential = (
            SocialAccountCredential.objects.filter(
                social_account=social_account
            )
            .first()
        )

        encrypted_refresh_token = None

        if refresh_token:
            encrypted_refresh_token = cls.encrypt(
                refresh_token
            )
        elif credential:
            encrypted_refresh_token = (
                credential.encrypted_refresh_token
            )

        if credential:
            credential.encrypted_access_token = (
                encrypted_access_token
            )
            credential.token_expires_at = (
                token_expires_at
            )

            # Only update refresh-token fields when the caller
            # actually provides refresh-token information.
            if refresh_token:
                credential.encrypted_refresh_token = (
                    encrypted_refresh_token
                )

                credential.refresh_token_expires_at = (
                    refresh_token_expires_at
                )

            credential.save()

            return credential, False

        credential = SocialAccountCredential.objects.create(
            social_account=social_account,
            encrypted_access_token=(
                encrypted_access_token
            ),
            encrypted_refresh_token=(
                encrypted_refresh_token
            ),
            token_expires_at=token_expires_at,
            refresh_token_expires_at=(
                refresh_token_expires_at
            ),
        )

        return credential, True

    # ==========================================================
    # UPDATE
    # ==========================================================

    @classmethod
    def update_credentials(
        cls,
        *,
        social_account,
        access_token=None,
        refresh_token=None,
        token_expires_at=None,
        refresh_token_expires_at=None,
    ):
        """
        Update an existing credential record.

        Only values explicitly supplied by the caller are
        changed.

        This prevents accidental deletion of existing
        credentials when a provider does not return a
        particular token.
        """

        credential = (
            SocialAccountCredential.objects.filter(
                social_account=social_account
            )
            .first()
        )

        if not credential:
            raise SocialAccountCredential.DoesNotExist(
                "No credentials found for this social account."
            )

        if access_token is not None:
            credential.encrypted_access_token = cls.encrypt(
                access_token
            )

        if refresh_token is not None:
            credential.encrypted_refresh_token = cls.encrypt(
                refresh_token
            )

        if token_expires_at is not None:
            credential.token_expires_at = (
                token_expires_at
            )

        if refresh_token_expires_at is not None:
            credential.refresh_token_expires_at = (
                refresh_token_expires_at
            )

        credential.save()

        return credential

    # ==========================================================
    # READ
    # ==========================================================

    @classmethod
    def get_credential(cls, social_account):
        """
        Return the credential database object.

        Tokens remain encrypted.
        """

        return (
            SocialAccountCredential.objects.filter(
                social_account=social_account
            )
            .first()
        )

    @classmethod
    def get_access_token(cls, social_account):
        """
        Retrieve and decrypt the access token.
        """

        credential = cls.get_credential(
            social_account
        )

        if not credential:
            return None

        return cls.decrypt(
            credential.encrypted_access_token
        )

    @classmethod
    def get_refresh_token(cls, social_account):
        """
        Retrieve and decrypt the refresh token.

        Returns None when the provider does not use a
        conventional refresh token.
        """

        credential = cls.get_credential(
            social_account
        )

        if not credential:
            return None

        if not credential.encrypted_refresh_token:
            return None

        return cls.decrypt(
            credential.encrypted_refresh_token
        )

    @classmethod
    def get_credentials(cls, social_account):
        """
        Retrieve and decrypt all stored credentials.

        This method returns plaintext tokens only in memory.
        They are never stored back into the database in
        plaintext.
        """

        credential = cls.get_credential(
            social_account
        )

        if not credential:
            return None

        return {
            "access_token": cls.decrypt(
                credential.encrypted_access_token
            ),
            "refresh_token": (
                cls.decrypt(
                    credential.encrypted_refresh_token
                )
                if credential.encrypted_refresh_token
                else None
            ),
            "token_expires_at": (
                credential.token_expires_at
            ),
            "refresh_token_expires_at": (
                credential.refresh_token_expires_at
            ),
        }

    # ==========================================================
    # DELETE
    # ==========================================================

    @classmethod
    def delete_credentials(cls, social_account):
        """
        Permanently delete stored credentials for a
        social account.
        """

        return (
            SocialAccountCredential.objects
            .filter(
                social_account=social_account
            )
            .delete()
        )