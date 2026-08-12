from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from .base import (
    BaseSocialProvider,
    OAuthTokenData,
    ProviderAccountData,
    ProviderConnectedAccount,
)


class FacebookProvider(BaseSocialProvider):
    """
    Meta/Facebook provider implementation.

    Responsibilities:
    - OAuth authorization URL generation
    - Authorization code exchange
    - Short-lived -> long-lived user token exchange
    - Facebook Page discovery
    - Page credential mapping
    - Access revocation

    Credential persistence is NOT handled here.

    Tokens are returned through OAuthTokenData and are
    persisted by CredentialService at the service layer.
    """

    platform = "facebook"

    GRAPH_API_VERSION = "v24.0"
    GRAPH_API_BASE_URL = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    )
    OAUTH_DIALOG_URL = (
        "https://www.facebook.com/dialog/oauth"
    )

    def __init__(self):
        self.app_id = settings.META_APP_ID
        self.app_secret = settings.META_APP_SECRET

    # ==========================================================
    # OAUTH AUTHORIZATION
    # ==========================================================

    def get_authorization_url(
        self,
        *,
        state: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> str:
        """
        Build Facebook OAuth authorization URL.
        """

        params = {
            "client_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(scopes),
        }

        return (
            f"{self.OAUTH_DIALOG_URL}?"
            f"{urlencode(params)}"
        )

    # ==========================================================
    # AUTHORIZATION CODE -> USER ACCESS TOKEN
    # ==========================================================

    def exchange_code_for_token(
        self,
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokenData:
        """
        Exchange Facebook authorization code for a
        short-lived user access token.
        """

        response = requests.get(
            f"{self.GRAPH_API_BASE_URL}/oauth/access_token",
            params={
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        expires_at = None

        if data.get("expires_in"):
            expires_at = (
                timezone.now()
                + timedelta(
                    seconds=int(data["expires_in"])
                )
            )

        return OAuthTokenData(
            access_token=data["access_token"],
            expires_at=expires_at,
            scopes=[],
            raw_data=data,
        )

    # ==========================================================
    # FACEBOOK PAGE DISCOVERY
    # ==========================================================

    def get_accounts(
        self,
        *,
        access_token: str,
    ) -> list[ProviderConnectedAccount]:
        """
        Discover Facebook Pages accessible by the supplied
        Facebook user access token.

        Returns:
            List[ProviderConnectedAccount]

        Each result contains:

        account:
            Non-sensitive Facebook Page information.

        credential:
            Page Access Token as access_token.
            Facebook User Access Token as refresh_token.

        IMPORTANT:
        Tokens are NEVER placed inside account.metadata.
        """

        response = requests.get(
            f"{self.GRAPH_API_BASE_URL}/me/accounts",
            params={
                "access_token": access_token,
                "fields": (
                    "id,name,access_token,"
                    "category,picture"
                ),
            },
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        accounts = []

        for page in data.get("data", []):

            page_id = page.get("id")
            page_name = page.get("name")
            page_access_token = page.get(
                "access_token"
            )

            if not page_id:
                continue

            if not page_name:
                continue

            if not page_access_token:
                continue

            picture = page.get("picture") or {}

            picture_data = (
                picture.get("data") or {}
            )

            avatar_url = picture_data.get("url")

            # --------------------------------------------------
            # NON-SENSITIVE ACCOUNT DATA
            # --------------------------------------------------

            account = ProviderAccountData(
                platform="facebook",
                platform_account_id=page_id,
                display_name=page_name,
                account_type="page",
                avatar_url=avatar_url,
                metadata={
                    "category": page.get("category"),
                },
            )

            # --------------------------------------------------
            # SENSITIVE CREDENTIAL DATA
            # --------------------------------------------------
            #
            # access_token:
            #     Facebook Page Access Token
            #
            # refresh_token:
            #     Facebook User Access Token that was used
            #     to discover the Page.
            #
            # Both values are only kept in memory here.
            # CredentialService will encrypt them before DB
            # persistence.
            # --------------------------------------------------

            credential = OAuthTokenData(
                access_token=page_access_token,
                refresh_token=access_token,
                expires_at=None,
                refresh_token_expires_at=None,
                scopes=[],
                raw_data={
                    "source": "facebook_page_discovery",
                },
            )

            accounts.append(
                ProviderConnectedAccount(
                    account=account,
                    credential=credential,
                )
            )

        return accounts

    # ==========================================================
    # FACEBOOK USER TOKEN LIFECYCLE
    # ==========================================================

    def refresh_access_token(
        self,
        *,
        refresh_token: str,
    ) -> OAuthTokenData:
        """
        Facebook does not use a conventional OAuth refresh
        token.

        For this provider, refresh_token represents the
        existing Facebook user access token.

        Facebook exchanges that token for a long-lived
        user access token.
        """

        response = requests.get(
            f"{self.GRAPH_API_BASE_URL}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": refresh_token,
            },
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        expires_at = None

        if data.get("expires_in"):
            expires_at = (
                timezone.now()
                + timedelta(
                    seconds=int(data["expires_in"])
                )
            )

        return OAuthTokenData(
            access_token=data["access_token"],
            expires_at=expires_at,
            scopes=[],
            raw_data=data,
        )

    # ==========================================================
    # ACCESS REVOCATION
    # ==========================================================

    def revoke_access(
        self,
        *,
        access_token: str,
    ) -> bool:
        """
        Revoke Facebook permissions for the supplied
        access token.
        """

        response = requests.delete(
            f"{self.GRAPH_API_BASE_URL}/me/permissions",
            params={
                "access_token": access_token,
            },
            timeout=20,
        )

        if not response.ok:
            return False

        data = response.json()

        return bool(data.get("success"))