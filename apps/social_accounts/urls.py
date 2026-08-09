from django.urls import path
from .views import FacebookCallbackView, FacebookConnectView

app_name = "social_accounts"

urlpatterns = [
    path("facebook/connect/", FacebookConnectView.as_view(), name="facebook-connect"),
    path("facebook/callback/", FacebookCallbackView.as_view(), name="facebook-callback"),
]