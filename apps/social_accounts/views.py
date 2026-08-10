from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.shortcuts import redirect
from apps.accounts.models import User
from .providers.facebook import FacebookProvider
from .services.social_account_service import SocialAccountService
from apps.workspaces.models import Workspace
from apps.social_accounts.services.oauth_state import OAuthStateService, InvalidOAuthState


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
        accounts = SocialAccountService.connect_facebook(
            code=code,
            redirect_uri=redirect_uri,
            state_obj=state_obj
        )

        return JsonResponse({
            "message": "Facebook connected successfully",
            "accounts": accounts
        })