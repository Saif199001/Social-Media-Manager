from django.conf import settings
from django.http import JsonResponse
from django.views import View
import requests
from apps.accounts.models import User
from .providers.facebook import FacebookProvider

from apps.workspaces.models import Workspace
from apps.social_accounts.services.oauth_state import OAuthStateService


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

        return JsonResponse({
            "auth_url": auth_url
        })
    

class FacebookCallbackView(View):

    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code or not state:
            return JsonResponse({"error": "Missing code or state"}, status=400)

        # ✅ STEP 1: Verify state
        try:
            state_obj = OAuthStateService.verify_state(state)
        except Exception:
            return JsonResponse({"error": "Invalid or expired state"}, status=400)

        # ✅ STEP 2: Exchange code for access token
        token_url = "https://graph.facebook.com/v19.0/oauth/access_token"

        token_params = {
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": "https://social-media-manager-hgqy.onrender.com/api/v1/social-accounts/facebook/callback/",
            "code": code,
        }

        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            return JsonResponse({
                "error": "Failed to get access token",
                "details": token_data
            }, status=400)

        # ✅ STEP 3: Fetch Facebook Pages
        pages_url = "https://graph.facebook.com/v19.0/me/accounts"

        pages_response = requests.get(pages_url, params={
            "access_token": access_token
        })

        pages_data = pages_response.json()

        # ✅ FINAL RESPONSE
        return JsonResponse({
            "message": "Facebook connected successfully",
            "access_token": access_token,
            "pages": pages_data
        })