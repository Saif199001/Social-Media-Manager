from django.utils import timezone

from apps.social_accounts.models import SocialAccount, SocialAccountCredential
from apps.social_accounts.providers.facebook import FacebookProvider


class SocialAccountService:

    # =========================
    # TOKEN LIFECYCLE METHODS
    # =========================

    @staticmethod
    def is_token_expired(credential):
        if not credential.token_expires_at:
            return False
        return credential.token_expires_at <= timezone.now()

    @staticmethod
    def refresh_facebook_token(social_account):
        """
        Refresh Facebook long-lived USER token.
        NOTE:
        - Page token refresh nahi hota
        - User token refresh hota hai
        """

        provider = FacebookProvider()

        user_token = social_account.metadata.get("user_access_token")

        if not user_token:
            return None

        new_token_data = provider.refresh_access_token(
            refresh_token=user_token
        )

        # ✅ Update user token in metadata
        social_account.metadata["user_access_token"] = new_token_data.access_token
        social_account.save(update_fields=["metadata"])

        # ✅ Update expiry in credential
        credential = social_account.credential
        credential.token_expires_at = new_token_data.expires_at
        credential.save(update_fields=["token_expires_at"])

        return new_token_data

    @staticmethod
    def get_valid_token(social_account):
        """
        Always return valid PAGE access token
        """

        credential = social_account.credential

        if SocialAccountService.is_token_expired(credential):
            SocialAccountService.refresh_facebook_token(social_account)

        return credential.encrypted_access_token

    # =========================
    # FACEBOOK CONNECT FLOW
    # =========================

    @staticmethod
    def connect_facebook(*, code, redirect_uri, state_obj):

        provider = FacebookProvider()

        # ✅ STEP 1: Exchange code → short-lived user token
        token_data = provider.exchange_code_for_token(
            code=code,
            redirect_uri=redirect_uri
        )

        short_lived_token = token_data.access_token

        # ✅ STEP 2: Convert → long-lived user token
        long_lived_token_data = provider.refresh_access_token(
            refresh_token=short_lived_token
        )

        user_access_token = long_lived_token_data.access_token
        expires_at = long_lived_token_data.expires_at

        # ✅ STEP 3: Fetch pages
        accounts = provider.get_accounts(
            access_token=user_access_token
        )

        saved_accounts = []

        for acc in accounts:

            # ✅ Page token (IMPORTANT)
            page_token = acc.metadata.get("page_access_token")

            if not page_token:
                continue  # skip invalid pages

            # ✅ STEP 4: Save SocialAccount
            social_account, _ = SocialAccount.objects.update_or_create(
                workspace=state_obj.workspace,
                platform="facebook",
                platform_account_id=acc.platform_account_id,
                defaults={
                    "display_name": acc.display_name,
                    "account_type": acc.account_type,
                    "avatar_url": acc.avatar_url,
                    "metadata": {
                        **acc.metadata,
                        "user_access_token": user_access_token
                    },
                    "connected_by": state_obj.user,
                    "connection_status": "connected",
                }
            )

            # ✅ STEP 5: Save Credentials (ONLY PAGE TOKEN)
            SocialAccountCredential.objects.update_or_create(
                social_account=social_account,
                defaults={
                    "encrypted_access_token": page_token,
                    "token_expires_at": expires_at,
                }
            )

            saved_accounts.append({
                "id": str(social_account.id),
                "name": social_account.display_name
            })

        return saved_accounts