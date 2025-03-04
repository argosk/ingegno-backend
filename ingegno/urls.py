"""
URL configuration for visitcity project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework_simplejwt.views import (
    # TokenObtainPairView,
    # TokenRefreshView,
    TokenBlacklistView
)

from api.views import CustomTokenRefreshView, CustomTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('api/', include('api.urls')),
    # path('api/blog/', include('blog.urls')),
    path('api/connected-accounts/', include('connected_accounts.urls')),
    path('api/workflows/', include('workflows.urls')),
    path('api/campaigns/', include('campaigns.urls')),
    path('api/leads/', include('leads.urls')),
    path('api/emails/', include('emails.urls')),
    # path('api/tracking/', include('tracking.urls')),
    path('api/payments/', include('subscriptions.urls')),
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)