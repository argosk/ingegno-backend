from django.urls import path
from .views import RegisterView, MeView, ChangePasswordView, ChangeEmailView, UpdateUserView

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('register/', RegisterView.as_view(), name='register'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('change-email/', ChangeEmailView.as_view(), name='change-email'),
    path('update/', UpdateUserView.as_view(), name='update_user'),
]
