from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class OAuthTokenData:
    """
    Generic OAuth credential/token data returned by a provider.

    This object contains sensitive token information and should
    only exist in memory until CredentialService persists it
    securely.
    """

    access_token: str

    refresh_token: Optional[str] = None

    expires_at: Optional[datetime] = None

    refresh_token_expires_at: Optional[datetime] = None

    scopes: List[str] = field(default_factory=list)

    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderAccountData:
    """
    Generic non-secret account information returned by a
    social platform provider.

    OAuth credentials must NOT be stored in this object.
    """

    platform: str

    platform_account_id: str

    display_name: str

    account_type: str

    username: Optional[str] = None

    avatar_url: Optional[str] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ProviderConnectedAccount:
    """
    Represents one connected account discovered through
    a provider.

    account:
        Non-secret platform/account information.

    credential:
        OAuth credential information associated with that
        account. CredentialService is responsible for secure
        persistence.
    """

    account: ProviderAccountData

    credential: OAuthTokenData


class BaseSocialProvider:
    """
    Abstract contract for social media providers.

    Provider implementations handle platform-specific OAuth
    and API behavior.

    Credential persistence is handled outside the provider
    through CredentialService.
    """

    platform: str = ""

    def get_authorization_url(
        self,
        *,
        state: str,
        redirect_uri: str,
        scopes: List[str],
    ) -> str:
        raise NotImplementedError

    def exchange_code_for_token(
        self,
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokenData:
        raise NotImplementedError

    def refresh_access_token(
        self,
        *,
        refresh_token: str,
    ) -> OAuthTokenData:
        raise NotImplementedError

    def get_accounts(
        self,
        *,
        access_token: str,
    ) -> List[ProviderConnectedAccount]:
        raise NotImplementedError