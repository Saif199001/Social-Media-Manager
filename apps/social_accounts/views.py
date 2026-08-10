from django.conf import settings
import logging
from django.http import JsonResponse
from django.views import View
from django.shortcuts import redirect
from apps.accounts.models import User
from .providers.facebook import FacebookProvider
from .services.social_account_service import SocialAccountService
from apps.workspaces.models import Workspace
from apps.social_accounts.services.oauth_state import OAuthStateService, InvalidOAuthState


logger = logging.getLogger(__name__)

class FacebookConnectView(View):

    def get(self, request):

        user = User.objects.first() # temporary
        workspace = Workspace.objects.first()  # temporary

        raw_state = OAuthStateService.create_state(
            user=user,
            workspace=workspace,
            platform="facebook",
        )

        provider = FacebookProvider()

        redirect_uri = "https://social-media-manager-hgqy.onrender.com/api/v1/social-accounts/facebook/callback/"

        scopes = [
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
        ]

        auth_url = provider.get_authorization_url(
            state=raw_state,
            redirect_uri=redirect_uri,
            scopes=scopes,
        )

        return redirect(auth_url)
    

class FacebookCallbackView(View):


    def get(self, request):

        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code or not state:
            return JsonResponse({"error": "Missing code or state"}, status=400)

        try:
            state_obj = OAuthStateService.consume_state(raw_state=state)
        except InvalidOAuthState:
            return JsonResponse({"error": "Invalid or expired state"}, status=400)

        redirect_uri = "https://social-media-manager-hgqy.onrender.com/api/v1/social-accounts/facebook/callback/"

        # ✅ SERVICE CALL
        try:
            accounts = SocialAccountService.connect_facebook(
                code=code,
                redirect_uri=redirect_uri,
                state_obj=state_obj
            )

        except Exception:
            logger.exception("FACEBOOK_OAUTH_CALLBACK_FAILED")
            return JsonResponse(
                {
                    "error": "Facebook connection failed"
                },
                status=500
            )