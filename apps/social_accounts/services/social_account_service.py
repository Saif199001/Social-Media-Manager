from django.utils import timezone

from apps.social_accounts.models import SocialAccount
from apps.social_accounts.providers.facebook import FacebookProvider
from apps.social_accounts.services.credential_service import (
    CredentialService,
)


class SocialAccountService:

    # ==========================================================
    # TOKEN LIFECYCLE
    # ==========================================================

    @staticmethod
    def is_token_expired(credential):
        """
        Check whether the primary access token has expired.
        """

        if not credential:
            return True

        if not credential.token_expires_at:
            return False

        return credential.token_expires_at <= timezone.now()

    @staticmethod
    def is_refresh_token_expired(credential):
        """
        Check whether the stored secondary/refresh credential
        has expired.
        """

        if not credential:
            return True

        if not credential.refresh_token_expires_at:
            return False

        return (
            credential.refresh_token_expires_at
            <= timezone.now()
        )

    @staticmethod
    def get_valid_token(social_account):
        """
        Return the decrypted primary access token.

        CredentialService handles decryption.
        """

        credential = CredentialService.get_credential(
            social_account
        )

        if not credential:
            raise ValueError(
                "No credentials found for this social account."
            )

        if SocialAccountService.is_token_expired(
            credential
        ):
            raise ValueError(
                "Social account access token has expired."
            )

        token = CredentialService.get_access_token(
            social_account
        )

        if not token:
            raise ValueError(
                "No access token found for this social account."
            )

        return token

    # ==========================================================
    # FACEBOOK CONNECT
    # ==========================================================

    @staticmethod
    def connect_facebook(
        *,
        code,
        redirect_uri,
        state_obj,
    ):
        """
        Connect Facebook Pages for the workspace represented
        by the validated OAuth state.

        Flow:

        Authorization code
            ↓
        short-lived user token
            ↓
        long-lived user token
            ↓
        Facebook Page discovery
            ↓
        Page SocialAccount
            ↓
        encrypted Page token + User token
        """

        provider = FacebookProvider()

        # ------------------------------------------------------
        # STEP 1
        # Authorization code -> short-lived user token
        # ------------------------------------------------------

        short_lived_token_data = (
            provider.exchange_code_for_token(
                code=code,
                redirect_uri=redirect_uri,
            )
        )

        short_lived_user_token = (
            short_lived_token_data.access_token
        )

        if not short_lived_user_token:
            raise ValueError(
                "Facebook did not return an access token."
            )

        # ------------------------------------------------------
        # STEP 2
        # Short-lived -> long-lived user token
        # ------------------------------------------------------

        long_lived_user_token_data = (
            provider.refresh_access_token(
                refresh_token=short_lived_user_token
            )
        )

        long_lived_user_token = (
            long_lived_user_token_data.access_token
        )

        if not long_lived_user_token:
            raise ValueError(
                "Facebook did not return a long-lived "
                "user access token."
            )

        # ------------------------------------------------------
        # STEP 3
        # Discover Facebook Pages
        # ------------------------------------------------------

        connected_accounts = provider.get_accounts(
            access_token=long_lived_user_token
        )

        saved_accounts = []

        # ------------------------------------------------------
        # STEP 4
        # Persist discovered accounts + credentials
        # ------------------------------------------------------

        for connected_account in connected_accounts:

            account_data = connected_account.account
            credential_data = connected_account.credential

            page_access_token = (
                credential_data.access_token
            )

            facebook_user_access_token = (
                credential_data.refresh_token
            )

            if not page_access_token:
                continue

            if not facebook_user_access_token:
                raise ValueError(
                    "Facebook user access token is missing."
                )

            # --------------------------------------------------
            # IMPORTANT
            #
            # account_data.metadata must contain ONLY
            # non-sensitive account information.
            # --------------------------------------------------

            account_metadata = dict(
                account_data.metadata or {}
            )

            social_account, _ = (
                SocialAccount.objects.update_or_create(
                    workspace=state_obj.workspace,
                    platform=account_data.platform,
                    platform_account_id=(
                        account_data.platform_account_id
                    ),
                    defaults={
                        "display_name": (
                            account_data.display_name
                        ),
                        "account_type": (
                            account_data.account_type
                        ),
                        "avatar_url": (
                            account_data.avatar_url
                        ),
                        "metadata": account_metadata,
                        "connected_by": state_obj.user,
                        "connection_status": "connected",
                    },
                )
            )

            # --------------------------------------------------
            # Credential persistence
            #
            # Primary access token:
            #     Facebook Page Access Token
            #
            # Refresh credential:
            #     Facebook Long-lived User Access Token
            #
            # Both are encrypted by CredentialService.
            # --------------------------------------------------

            CredentialService.save_credentials(
                social_account=social_account,
                access_token=page_access_token,
                refresh_token=facebook_user_access_token,
                token_expires_at=(
                    credential_data.expires_at
                ),
                refresh_token_expires_at=(
                    long_lived_user_token_data.expires_at
                ),
            )

            saved_accounts.append(
                {
                    "id": str(social_account.id),
                    "name": (
                        social_account.display_name
                    ),
                    "platform": (
                        social_account.platform
                    ),
                }
            )

        return saved_accounts

    # ==========================================================
    # FACEBOOK USER TOKEN REFRESH
    # ==========================================================

    @staticmethod
    def refresh_facebook_token(
        social_account,
    ):
        """
        Refresh the Facebook user access token and update
        the connected Page credentials.

        Facebook does not use a conventional refresh token.
        The encrypted refresh credential contains the
        long-lived Facebook user access token used for the
        next token exchange.
        """

        credential = CredentialService.get_credential(
            social_account
        )

        if not credential:
            raise ValueError(
                "No credentials found for this social account."
            )

        facebook_user_token = (
            CredentialService.get_refresh_token(
                social_account
            )
        )

        if not facebook_user_token:
            raise ValueError(
                "Facebook user access token is unavailable."
            )

        if SocialAccountService.is_refresh_token_expired(
            credential
        ):
            raise ValueError(
                "Facebook user access token has expired."
            )

        provider = FacebookProvider()

        # ------------------------------------------------------
        # STEP 1
        # Exchange existing Facebook user token
        # for a new long-lived user token
        # ------------------------------------------------------

        new_user_token_data = (
            provider.refresh_access_token(
                refresh_token=facebook_user_token
            )
        )

        new_user_token = (
            new_user_token_data.access_token
        )

        if not new_user_token:
            raise ValueError(
                "Facebook did not return a new user access token."
            )

        # ------------------------------------------------------
        # STEP 2
        # Rediscover Pages using the new user token
        # ------------------------------------------------------

        connected_accounts = provider.get_accounts(
            access_token=new_user_token
        )

        current_page_id = (
            social_account.platform_account_id
        )

        matching_account = None

        for connected_account in connected_accounts:

            if (
                connected_account.account
                .platform_account_id
                == current_page_id
            ):
                matching_account = connected_account
                break

        if not matching_account:
            raise ValueError(
                "Facebook Page could not be rediscovered "
                "using the refreshed user token."
            )

        new_page_token = (
            matching_account.credential.access_token
        )

        if not new_page_token:
            raise ValueError(
                "Facebook did not return a new Page access token."
            )

        # ------------------------------------------------------
        # STEP 3
        # Update encrypted credentials
        # ------------------------------------------------------

        CredentialService.update_credentials(
            social_account=social_account,
            access_token=new_page_token,
            refresh_token=new_user_token,
            token_expires_at=(
                matching_account.credential.expires_at
            ),
            refresh_token_expires_at=(
                new_user_token_data.expires_at
            ),
        )

        return new_page_token