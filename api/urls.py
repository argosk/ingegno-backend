from django.urls import include, path

from .views import (
    index, 
    ForgotPasswordView, 
    ResetPasswordView, 
    GoogleAuthURLView, 
    GoogleCallbackView,
    # TestEmailView,
)


urlpatterns = [
    path('', index, name='index'),
    path('users/', include('users.urls')),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('google-auth-url/', GoogleAuthURLView.as_view(), name='google_auth_url'),
    path('google/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    # path('test-email/', TestEmailView.as_view(), name='test_email'),
]
