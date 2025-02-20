from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConnectedAccountViewSet, OAuth2InitView, OAuth2CallbackView, OutlookOAuth2InitView, OutlookOAuth2CallbackView, IMAPSMTPAccountView

router = DefaultRouter()
router.register(r'', ConnectedAccountViewSet)

urlpatterns = [
    path('', include(router.urls)),  # Gestisce CRUD per ConnectedAccount
    path('gmail/oauth2/init/', OAuth2InitView.as_view(), name='oauth2-init'),  # Flusso OAuth2
    path('gmail/oauth2/callback/', OAuth2CallbackView.as_view(), name='oauth2-callback'),  # Callback OAuth2
    path('outlook/oauth2/init/', OutlookOAuth2InitView.as_view(), name='outlook-oauth2-init'),
    path('outlook/oauth2/callback/', OutlookOAuth2CallbackView.as_view(), name='outlook-oauth2-callback'),
    path('imap-smtp/connect/', IMAPSMTPAccountView.as_view(), name='imap-smtp-connect'),

]
