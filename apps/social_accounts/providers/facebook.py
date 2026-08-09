from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from .base import (
    BaseSocialProvider,
    OAuthTokenData,
    ProviderAccountData,
)


class FacebookProvider(BaseSocialProvider):
    """
    Meta/Facebook provider implementation.

    Handles:
    - OAuth authorization
    - Authorization code exchange
    - Facebook Page discovery
    - Long-lived user token exchange
    - Access revocation
    """

    provider_name = "facebook"

    GRAPH_API_VERSION = "v24.0"
    GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    OAUTH_DIALOG_URL = "https://www.facebook.com/dialog/oauth"

    def __init__(self):
        self.app_id = settings.META_APP_ID
        self.app_secret = settings.META_APP_SECRET

    def get_authorization_url(
        self,
        *,
        state: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> str:
        params = {
            "client_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(scopes),
        }

        return f"{self.OAUTH_DIALOG_URL}?{urlencode(params)}"

    def exchange_code_for_token(
        self,
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokenData:
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
            expires_at = timezone.now() + timedelta(
                seconds=int(data["expires_in"])
            )

        return OAuthTokenData(
            access_token=data["access_token"],
            expires_at=expires_at,
            scopes=[],
            raw_data=data,
        )

    def get_accounts(
        self,
        *,
        access_token: str,
    ) -> list[ProviderAccountData]:
        response = requests.get(
            f"{self.GRAPH_API_BASE_URL}/me/accounts",
            params={
                "access_token": access_token,
                "fields": "id,name,access_token,category,picture",
            },
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()

        accounts = []

        for page in data.get("data", []):
            picture = page.get("picture", {})
            avatar_url = (
                picture
                .get("data", {})
                .get("url")
            )

            accounts.append(
                ProviderAccountData(
                    platform="facebook",
                    platform_account_id=page["id"],
                    display_name=page["name"],
                    account_type="page",
                    avatar_url=avatar_url,
                    metadata={
                        "category": page.get("category"),
                        "page_access_token": page.get("access_token"),
                    },
                )
            )

        return accounts

    def refresh_access_token(
        self,
        *,
        refresh_token: str,
    ) -> OAuthTokenData:
        """
        Facebook does not use a conventional refresh token.

        For Facebook, this method exchanges a short-lived user
        access token for a long-lived user access token.

        The refresh_token argument therefore represents the
        existing Facebook user access token.
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
            expires_at = timezone.now() + timedelta(
                seconds=int(data["expires_in"])
            )

        return OAuthTokenData(
            access_token=data["access_token"],
            expires_at=expires_at,
            scopes=[],
            raw_data=data,
        )

    def revoke_access(
        self,
        *,
        access_token: str,
    ) -> bool:
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