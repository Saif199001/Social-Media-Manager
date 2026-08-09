from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class OAuthTokenData:
    """
    Normalized OAuth token data returned by any provider.
    """

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    refresh_token_expires_at: Optional[datetime] = None
    scopes: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderAccountData:
    """
    Normalized social account data returned by any provider.
    """

    platform: str
    platform_account_id: str
    display_name: str

    account_type: str = "other"
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSocialProvider(ABC):
    """
    Base contract for all social media providers.

    Every provider adapter such as Meta, LinkedIn or YouTube
    must implement this interface.
    """

    provider_name: str = ""

    @abstractmethod
    def get_authorization_url(
        self,
        *,
        state: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> str:
        """
        Generate provider OAuth authorization URL.
        """
        raise NotImplementedError

    @abstractmethod
    def exchange_code_for_token(
        self,
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokenData:
        """
        Exchange OAuth authorization code for token data.
        """
        raise NotImplementedError

    @abstractmethod
    def get_accounts(
        self,
        *,
        access_token: str,
    ) -> list[ProviderAccountData]:
        """
        Fetch social accounts/pages/channels available
        through the authenticated provider identity.
        """
        raise NotImplementedError

    @abstractmethod
    def refresh_access_token(
        self,
        *,
        refresh_token: str,
    ) -> OAuthTokenData:
        """
        Refresh an expired or expiring access token.

        Providers that do not support conventional refresh tokens
        should implement their provider-specific refresh mechanism.
        """
        raise NotImplementedError

    @abstractmethod
    def revoke_access(
        self,
        *,
        access_token: str,
    ) -> bool:
        """
        Revoke/disconnect provider authorization.
        """
        raise NotImplementedError